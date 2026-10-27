#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# Build only the Unix ntdll corresponding to Highball's pinned CX26.3-r27 engine.
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TOOLCHAIN_BIN=${1:?usage: build-ntdll-macos.sh LLVM_MINGW_BIN FRESH_WORK_DIR OUTPUT_DIR [SOURCE_ARCHIVE]}
WORK=${2:?fresh work directory required}
OUTPUT=${3:?output directory required}
SOURCE_ARCHIVE=${4:-}
JOBS=${JOBS:-4}

[ "$(uname -s)" = Darwin ] || { echo 'This script builds a macOS x86_64 library.' >&2; exit 1; }
[ -x "$TOOLCHAIN_BIN/i686-w64-mingw32-gcc" ]
[ -x "$TOOLCHAIN_BIN/x86_64-w64-mingw32-gcc" ]
[ -f "$ROOT/inputs.json" ]
[ ! -e "$WORK/source" ] && [ ! -e "$WORK/build" ] || {
    echo 'Refusing an existing source/build tree; select a fresh work directory.' >&2; exit 1;
}
mkdir -p "$WORK" "$OUTPUT"
WORK=$(CDPATH= cd -- "$WORK" && pwd)
OUTPUT=$(CDPATH= cd -- "$OUTPUT" && pwd)
TOOLCHAIN_BIN=$(CDPATH= cd -- "$TOOLCHAIN_BIN" && pwd)

# Keep the old system Bison untouched. Prefer a separately installed Homebrew Bison.
if command -v brew >/dev/null 2>&1; then
    BISON_PREFIX=$(brew --prefix bison 2>/dev/null || true)
    if [ -n "$BISON_PREFIX" ] && [ -x "$BISON_PREFIX/bin/bison" ]; then
        export PATH="$BISON_PREFIX/bin:$TOOLCHAIN_BIN:$PATH"
    else
        export PATH="$TOOLCHAIN_BIN:$PATH"
    fi
else
    export PATH="$TOOLCHAIN_BIN:$PATH"
fi
bison --version | head -1
/usr/bin/arch -x86_64 /usr/bin/true

URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wine"]["url"])' "$ROOT/inputs.json")
EXPECTED=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wine"]["sha256"])' "$ROOT/inputs.json")
ARCHIVE="$WORK/crossover-sources-26.3.0.tar.gz"
if [ -n "$SOURCE_ARCHIVE" ]; then
    if [ "$SOURCE_ARCHIVE" != "$ARCHIVE" ]; then cp "$SOURCE_ARCHIVE" "$ARCHIVE"; fi
else
    curl -fL --retry 3 -o "$ARCHIVE" "$URL"
fi
printf '%s  %s\n' "$EXPECTED" "$ARCHIVE" | shasum -a 256 -c -
mkdir "$WORK/source" "$WORK/build"
COPYFILE_DISABLE=1 tar -xzf "$ARCHIVE" -C "$WORK/source"

python3 - "$ROOT" "$WORK" "$OUTPUT" <<'PY'
from pathlib import Path
import hashlib, json, subprocess, sys
root, work, output = map(Path, sys.argv[1:])
selected = []
for patch in sorted((root / 'patches').glob('*.patch')):
    number = int(patch.name[:4])
    if (number <= 24 and number != 13) or number in (28, 29, 30):
        selected.append(patch)
expected = [1, 2, 3] + list(range(5, 13)) + list(range(14, 25)) + [28, 29, 30]
assert [int(p.name[:4]) for p in selected] == expected, 'Unexpected patch series'
records = []
for patch in selected:
    print('applying', patch.name, flush=True)
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'],
                   cwd=work / 'source/sources/wine', input=patch.read_bytes(), check=True)
    records.append({'file': patch.name, 'sha256': hashlib.sha256(patch.read_bytes()).hexdigest()})
(output / 'PATCHES.json').write_text(json.dumps(records, indent=2) + '\n')
PY

cd "$WORK/build"
# Absolute Apple clang paths are essential: llvm-mingw's clang does not locate
# the Apple SDK correctly for this native side when it comes first on PATH.
if ! ../source/sources/wine/configure \
    --build=x86_64-apple-darwin --host=x86_64-apple-darwin \
    --enable-archs=i386,x86_64 --with-mingw \
    --without-alsa --without-capi --without-coreaudio --without-cups --without-dbus \
    --without-fontconfig --without-freetype --without-gnutls --without-gphoto \
    --without-gstreamer --without-krb5 --without-netapi --without-oss --without-pulse \
    --without-sane --without-sdl --without-udev --without-usb --without-v4l2 \
    --without-x --without-vulkan --disable-tests \
    CC='/usr/bin/clang -arch x86_64' CXX='/usr/bin/clang++ -arch x86_64' \
    CFLAGS='-O2 -mmacosx-version-min=14.0' LDFLAGS='-Wl,-headerpad_max_install_names' \
    > configure.log 2>&1; then
    tail -60 configure.log >&2; exit 1
fi
if ! make -j"$JOBS" dlls/ntdll/ntdll.so > ntdll-build.log 2>&1; then
    tail -60 ntdll-build.log >&2; exit 1
fi
cp dlls/ntdll/ntdll.so "$OUTPUT/ntdll.so"
if [ "${STRIP_NTDLL:-0}" = 1 ]; then
    strip -x -S "$OUTPUT/ntdll.so"
fi
codesign -f -s - "$OUTPUT/ntdll.so"
lipo -verify_arch x86_64 "$OUTPUT/ntdll.so"
codesign --verify --verbose "$OUTPUT/ntdll.so"
otool -L "$OUTPUT/ntdll.so" | tee "$OUTPUT/NTDLL-LINKS.txt"
cp configure.log ntdll-build.log "$OUTPUT/"
cp include/config.h "$OUTPUT/CONFIG.h"
shasum -a 256 "$OUTPUT/ntdll.so" > "$OUTPUT/ntdll.so.sha256"
python3 - "$ROOT" "$OUTPUT" "$TOOLCHAIN_BIN" <<'PY'
from pathlib import Path
import hashlib, json, os, subprocess, sys
root, output, toolchain = map(Path, sys.argv[1:])
def capture(args):
    r = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    return r.stdout.strip()
try:
    fork_commit = capture(['git', '-C', str(root), 'rev-parse', 'HEAD'])
except subprocess.CalledProcessError:
    recorded = root / 'BUILD-COMMIT.txt'
    fork_commit = recorded.read_text().strip() if recorded.is_file() else 'source archive; see patch checksums'
meta = {
    'source': json.loads((root / 'inputs.json').read_text())['wine'],
    'fork_commit': fork_commit,
    'target': 'dlls/ntdll/ntdll.so', 'architecture': 'x86_64',
    'deployment_target': '14.0', 'stripped': os.environ.get('STRIP_NTDLL', '0') == '1',
    'clang': capture(['/usr/bin/clang', '--version']),
    'sdk': capture(['xcrun', '--show-sdk-path']),
    'bison': capture(['bison', '--version']),
    'mingw': capture([str(toolchain / 'x86_64-w64-mingw32-gcc'), '--version']),
    'ntdll_sha256': hashlib.sha256((output / 'ntdll.so').read_bytes()).hexdigest(),
}
(output / 'BUILD-NTDLL.json').write_text(json.dumps(meta, indent=2) + '\n')
PY
printf 'Built: %s\n' "$OUTPUT/ntdll.so"
