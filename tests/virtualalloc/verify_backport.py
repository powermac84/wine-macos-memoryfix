#!/usr/bin/env python3
"""Prove the pinned baseline fails and the backported allocator passes."""
import pathlib
import subprocess
import sys
import tarfile
import tempfile

patched = pathlib.Path(sys.argv[1]).resolve()
archive = pathlib.Path(sys.argv[2]).resolve()
harness = pathlib.Path(__file__).with_name('check_map_boundaries.py')
with tempfile.TemporaryDirectory(prefix='wine-baseline-') as tmp:
    baseline = pathlib.Path(tmp) / 'virtual.c'
    with tarfile.open(archive) as source:
        member = source.getmember('sources/wine/dlls/ntdll/unix/virtual.c')
        baseline.write_bytes(source.extractfile(member).read())
    old = subprocess.run([sys.executable, str(harness), str(baseline)], timeout=30)
    if old.returncode != 1:
        raise SystemExit('Baseline did not reproduce the expected boundary bug')
    new = subprocess.run([sys.executable, str(harness), str(patched)], timeout=30)
    if new.returncode:
        raise SystemExit('Patched allocator regression failed')
print('PASS: pinned baseline reproduces boundary violations; patched allocator prevents them')
