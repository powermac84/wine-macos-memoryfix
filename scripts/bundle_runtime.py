#!/usr/bin/env python3
"""Prepare Wine's dynamic library names, then bundle its macOS runtime closure.

prepare CONFIG: run after configure, before compiling; records original SONAMEs.
bundle CONFIG ENGINE: run after installing Wine. System dylibs stay system dylibs;
all other linked dependencies must resolve to a bundled engine file or Homebrew.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse

KEYS = ('LIBVULKAN', 'LIBFREETYPE', 'LIBGNUTLS', 'LIBSDL2')
MAGICS = {b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
          b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
          b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'}


def run(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def state_path(config):
    return config.with_name('runtime-sonames.json')


def prepare(config):
    text = config.read_text()
    old = {}
    for key in KEYS:
        pattern = r'(#define SONAME_' + key + r' )"([^"]+)"'
        m = re.search(pattern, text)
        if not m:
            raise SystemExit('Missing required SONAME_' + key + ' in ' + str(config))
        original = m.group(2)
        if original.startswith('@rpath/'):
            raise SystemExit('Config already prepared; refusing to lose original SONAMEs')
        old[key] = original
        text = re.sub(pattern, lambda m: m.group(1) + '"@rpath/' + Path(original).name + '"', text)
    state_path(config).write_text(json.dumps(old, indent=2) + '\n')
    config.write_text(text)
    print('Prepared dynamic SONAMEs:', json.dumps(old), flush=True)


def is_macho(p):
    if not p.is_file() or p.is_symlink():
        return False
    with p.open('rb') as f:
        return f.read(4) in MAGICS


def load_commands(p):
    refs = [line.strip().split(' (compatibility version', 1)[0]
            for line in run('otool', '-L', p).splitlines()[1:] if line.strip()]
    detail = run('otool', '-l', p).splitlines()
    rpaths = []
    for i, line in enumerate(detail):
        if line.strip() == 'cmd LC_RPATH':
            for later in detail[i+1:i+5]:
                m = re.match(r'\s*path (.*?) \(offset \d+\)', later)
                if m:
                    rpaths.append(m.group(1))
                    break
    return refs, rpaths


def is_system(ref):
    return ref.startswith(('/System/Library/', '/usr/lib/'))


def inside(path, directory):
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def resolve(ref, origin, rpaths, brew_prefix, engine):
    if is_system(ref):
        return None
    origin = origin.resolve()
    if ref.startswith('@loader_path/'):
        candidates = [origin.parent / ref[len('@loader_path/'):]]
    elif ref.startswith('@executable_path/'):
        candidates = [engine / 'bin' / ref[len('@executable_path/'):]]
    elif ref.startswith('@rpath/'):
        tail = ref[len('@rpath/'):]
        candidates = []
        for rp in rpaths:
            if rp.startswith('@loader_path/'):
                candidates.append(origin.parent / rp[len('@loader_path/'):] / tail)
            elif rp == '@loader_path':
                candidates.append(origin.parent / tail)
            elif rp.startswith('@executable_path/'):
                candidates.append(engine / 'bin' / rp[len('@executable_path/'):] / tail)
            elif rp.startswith('/'):
                candidates.append(Path(rp) / tail)
        candidates.extend([origin.parent / tail, brew_prefix / 'lib' / tail])
    elif ref.startswith('/'):
        candidates = [Path(ref)]
    else:
        candidates = [origin.parent / ref, brew_prefix / 'lib' / ref]
    for path in candidates:
        if path.is_file():
            path = path.resolve()
            if inside(path, engine):
                return path
            if inside(path, brew_prefix):
                return path
            raise RuntimeError('Non-system dependency outside Homebrew/engine: %s -> %s' % (ref, path))
    raise RuntimeError('Cannot resolve dependency %s of %s (rpaths=%s)' % (ref, origin, rpaths))


def bundle(config, engine, sources_output=None):
    brew_prefix = Path(run('brew', '--prefix')).resolve()
    sonames = json.loads(state_path(config).read_text())
    dest = engine / 'lib'
    dest.mkdir(parents=True, exist_ok=True)
    originals = [p for p in engine.rglob('*') if is_macho(p)]
    todo = []
    for value in sonames.values():
        leaf = Path(value).name
        if Path(value).is_absolute():
            path = Path(value)
        else:
            path = brew_prefix / 'lib' / leaf
        if not path.is_file():
            raise RuntimeError('Configured SONAME not installed: ' + str(path))
        todo.append((leaf, path.resolve()))
    # Recent Homebrew SDL2 is sdl2-compat, which opens libSDL3.dylib at runtime.
    sdl3 = brew_prefix / 'lib/libSDL3.0.dylib'
    if sdl3.is_file():
        todo.append(('libSDL3.0.dylib', sdl3.resolve()))
    dependencies = {}
    seen = {}
    for origin in originals:
        refs, rpaths = load_commands(origin)
        dependencies[origin] = []
        for ref in refs:
            target = resolve(ref, origin, rpaths, brew_prefix, engine)
            if target:
                dependencies[origin].append((ref, target))
                if not inside(target, engine):
                    todo.append((Path(ref).name, target))
    while todo:
        leaf, source = todo.pop()
        if leaf in seen:
            if source != seen[leaf] and hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(seen[leaf].read_bytes()).digest():
                raise RuntimeError('Two different dylibs use name ' + leaf)
            continue
        seen[leaf] = source
        refs, rpaths = load_commands(source)
        dependencies[source] = []
        own_id = run('otool', '-D', source).splitlines()[-1]
        for ref in refs:
            if ref == source.as_posix() or ref == own_id:
                continue  # dylib's own LC_ID_DYLIB is not a dependency
            target = resolve(ref, source, rpaths, brew_prefix, engine)
            if target:
                dependencies[source].append((ref, target))
                if not inside(target, engine):
                    todo.append((Path(ref).name, target))
    by_source = {}
    for leaf, source in seen.items():
        by_source.setdefault(source, leaf)
        output = dest / leaf
        shutil.copy2(source, output)
        output.chmod(0o755)
    mapping = {source: dest / leaf for source, leaf in by_source.items()}
    def output_of(source):
        return source if inside(source, engine) else mapping[source]
    def local_ref(origin, target):
        return '@loader_path/' + os.path.relpath(target, origin.parent)
    rewritten = []
    for source in list(originals) + list(mapping):
        output = output_of(source)
        refs, rpaths = load_commands(output)
        for ref, target in dependencies.get(source, []):
            new = local_ref(output, output_of(target))
            if new != ref:
                run('install_name_tool', '-change', ref, new, output)
        # All dynamically opened @rpath SONAMEs find engine/lib from their caller.
        rp = local_ref(output, dest)
        if rp not in rpaths:
            run('install_name_tool', '-add_rpath', rp, output)
        if source in mapping:
            run('install_name_tool', '-id', '@loader_path/' + output.name, output)
        rewritten.append(output)
    # Keep alternative SONAME aliases if multiple original names resolved to one file.
    for leaf, source in seen.items():
        if leaf != by_source[source]:
            alias = dest / leaf
            alias.unlink()
            alias.symlink_to(by_source[source])
    if sdl3.is_file():
        alias = dest / 'libSDL3.dylib'
        if not alias.exists():
            alias.symlink_to('libSDL3.0.dylib')
    # Sign after all changes. No hardened runtime or third-party identity is added.
    for output in rewritten:
        run('lipo', '-verify_arch', 'x86_64', output)
        run('codesign', '-f', '-s', '-', '--preserve-metadata=entitlements', output)
    for output in rewritten:
        refs, rpaths = load_commands(output)
        for ref in refs:
            if ref.startswith((str(brew_prefix), '/opt/homebrew/', '/usr/local/')):
                raise RuntimeError('Non-portable dependency remains: %s in %s' % (ref, output))
    # Exercise each relocated root without DYLD search-path helpers.
    clean_env = os.environ.copy()
    for key in list(clean_env):
        if key.startswith('DYLD_'):
            clean_env.pop(key)
    for output in mapping.values():
        subprocess.run([sys.executable, '-c',
                        'import ctypes,sys; ctypes.CDLL(sys.argv[1])', str(output)],
                       env=clean_env, timeout=30, check=True)
    sdl_leaf = Path(sonames['LIBSDL2']).name
    subprocess.run([sys.executable, '-c',
                    'import ctypes,sys; s=ctypes.CDLL(sys.argv[1]); '
                    's.SDL_GetError.restype=ctypes.c_char_p; r=s.SDL_Init(0); '
                    'sys.exit("SDL_Init failed: %r" % s.SDL_GetError()) if r else s.SDL_Quit()',
                    str(dest / sdl_leaf)], env=clean_env, timeout=60, check=True)
    licenses = engine / 'share/runtime-licenses'
    licenses.mkdir(parents=True, exist_ok=True)
    formulae = {}
    for leaf, source in seen.items():
        parts = source.parts
        try:
            pos = parts.index('Cellar')
        except ValueError:
            raise RuntimeError('Cannot identify source formula for ' + str(source))
        name, version = parts[pos+1:pos+3]
        cellar = Path(*parts[:pos+3])
        if name not in formulae:
            metadata = json.loads(run('brew', 'info', '--json=v2', '--formula', name))['formulae'][0]
            formulae[name] = {'version': version, 'metadata': metadata, 'libraries': []}
            info_dest = licenses / (name + '-' + version)
            info_dest.mkdir(exist_ok=True)
            (info_dest / 'FORMULA.json').write_text(json.dumps(metadata, indent=2) + '\n')
            for f in [cellar / 'INSTALL_RECEIPT.json', *list((cellar / '.brew').glob('*'))]:
                if f.is_file():
                    shutil.copy2(f, info_dest / f.name)
            for directory in [cellar, cellar / 'share/licenses', cellar / 'share/doc' / name]:
                if not directory.is_dir():
                    continue
                for f in directory.rglob('*') if directory != cellar else directory.iterdir():
                    if f.is_file() and any(term in f.name.upper() for term in ('LICENSE', 'COPYING', 'COPYRIGHT', 'NOTICE', 'AUTHORS')):
                        target = info_dest / str(f.relative_to(cellar)).replace('/', '_')
                        shutil.copy2(f, target)
        formulae[name]['libraries'].append({'name': leaf, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    (licenses / 'DEPENDENCIES.json').write_text(json.dumps(formulae, indent=2) + '\n')
    if sources_output is None:
        sources_output = engine.parent / 'runtime-sources'
    sources_output.mkdir(parents=True, exist_ok=True)
    source_records = {}
    for name, record in formulae.items():
        stable_version = str(record['metadata']['versions'].get('stable'))
        if record['version'].split('_', 1)[0] != stable_version:
            raise RuntimeError('Installed/source version mismatch for %s: %s != %s' % (name, record['version'], stable_version))
        stable = record['metadata']['urls'].get('stable') or {}
        url = stable.get('url')
        checksum = stable.get('checksum')
        if not url or not checksum or not re.fullmatch(r'[0-9a-fA-F]{64}', checksum):
            raise RuntimeError('No SHA-256-pinned upstream source archive for formula ' + name)
        base = Path(urllib.parse.urlparse(url).path).name or 'source.tar'
        filename = re.sub(r'[^A-Za-z0-9._-]', '_', name + '-' + record['version'] + '-' + base)
        archive = sources_output / filename
        if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
            part = archive.with_name(archive.name + '.part')
            print('Fetching corresponding source for ' + name, flush=True)
            with urllib.request.urlopen(url, timeout=120) as response, part.open('wb') as out:
                shutil.copyfileobj(response, out)
            actual = hashlib.sha256(part.read_bytes()).hexdigest()
            if actual != checksum:
                raise RuntimeError('Source checksum mismatch for %s: %s != %s' % (name, actual, checksum))
            part.replace(archive)
        formula_dir = sources_output / (name + '-' + record['version'] + '-build-metadata')
        shutil.copytree(licenses / (name + '-' + record['version']), formula_dir, dirs_exist_ok=True)
        source_records[name] = {'installed_version': record['version'], 'url': url,
                                'sha256': checksum, 'archive': filename}
    (sources_output / 'SOURCES.json').write_text(json.dumps(source_records, indent=2) + '\n')
    print('Bundled runtime libraries:', ', '.join(sorted(seen)), flush=True)
    print('Runtime licensing metadata:', licenses, flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'bundle'])
    p.add_argument('config', type=Path)
    p.add_argument('engine', nargs='?', type=Path)
    p.add_argument('--sources-output', type=Path, help='default: ENGINE/../runtime-sources')
    args = p.parse_args()
    if args.mode == 'prepare':
        prepare(args.config.resolve())
    elif args.engine:
        bundle(args.config.resolve(), args.engine.resolve(),
               args.sources_output.resolve() if args.sources_output else None)
    else:
        p.error('bundle requires an engine directory')


if __name__ == '__main__':
    main()
