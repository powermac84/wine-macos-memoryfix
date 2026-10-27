#!/usr/bin/env python3
"""Run synthetic probes in disposable prefixes; a timeout or skip is a failure."""
import os
import pathlib
import subprocess
import sys

wine, programs, prefix_root, results = map(lambda p: pathlib.Path(p).resolve(), sys.argv[1:])
results.mkdir(parents=True, exist_ok=True)
server = wine.with_name('wineserver')
for test in ['virtualalloc-x86-laa', 'virtualalloc-x86-nonlaa', 'virtualalloc-x64']:
    prefix = prefix_root / test
    if prefix.exists():
        raise SystemExit('Refusing to reuse an existing test prefix: ' + str(prefix))
    prefix.mkdir(parents=True)
    env = os.environ.copy()
    for key in ['WINEPREFIX', 'WINEARCH', 'WINEDLLPATH_PREPEND', 'WINEDLLOVERRIDES',
                'WINE_LARGE_ADDRESS_AWARE', 'WINEESYNC', 'WINEFSYNC', 'WINEMSYNC']:
        env.pop(key, None)
    env.update(WINEPREFIX=str(prefix), WINEARCH='win64', WINEDEBUG='-all',
               WINEDLLOVERRIDES='winemenubuilder.exe,mscoree,mshtml=d',
               WINEESYNC='0', WINEFSYNC='0', WINEMSYNC='0')
    try:
        with (results / (test + '-boot.log')).open('w') as log:
            subprocess.run([str(wine), 'wineboot', '-u'], env=env, stdout=log,
                           stderr=subprocess.STDOUT, timeout=120, check=True)
            subprocess.run([str(server), '-w'], env=env, stdout=log,
                           stderr=subprocess.STDOUT, timeout=60, check=True)
        command = [str(wine), str(programs / (test + '.exe'))]
        if 'x86-' in test:
            command.append('--require-wow64')
        with (results / (test + '.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=60, check=True)
        output = (results / (test + '.log')).read_text(errors='replace')
        if 'RESULT failures=0 ' not in output or 'probes=56' not in output:
            raise RuntimeError('Probe did not report all 56 checks: ' + test)
        print('PASS:', test, flush=True)
    finally:
        subprocess.run([str(server), '-k'], env=env, timeout=15, check=False)
