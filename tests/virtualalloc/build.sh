#!/bin/sh
set -eu
OUT=${1:?output directory}
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CC32=${CC32:-i686-w64-mingw32-gcc}
CC64=${CC64:-x86_64-w64-mingw32-gcc}
mkdir -p "$OUT"
"$CC32" -O2 -Wall -Wextra -Werror -Wl,--large-address-aware "$HERE/virtualalloc_probe.c" -o "$OUT/virtualalloc-x86-laa.exe"
"$CC32" -O2 -Wall -Wextra -Werror "$HERE/virtualalloc_probe.c" -o "$OUT/virtualalloc-x86-nonlaa.exe"
"$CC64" -O2 -Wall -Wextra -Werror "$HERE/virtualalloc_probe.c" -o "$OUT/virtualalloc-x64.exe"

python3 - "$OUT" <<'PYVERIFY'
import pathlib, struct, sys
root = pathlib.Path(sys.argv[1])
for name, expected in [('virtualalloc-x86-laa', True), ('virtualalloc-x86-nonlaa', False)]:
    data = (root / (name + '.exe')).read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    assert bool(struct.unpack_from('<H', data, pe + 22)[0] & 0x20) == expected, name
print('PE flags verified: x86 LAA enabled/disabled as requested')
PYVERIFY
