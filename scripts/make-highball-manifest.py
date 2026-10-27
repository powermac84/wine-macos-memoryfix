#!/usr/bin/env python3
"""Create a Highball manifest from the public reference and a verified release."""
import argparse
import hashlib
import json
import pathlib
import urllib.parse

p = argparse.ArgumentParser()
p.add_argument('reference', type=pathlib.Path)
p.add_argument('archive', type=pathlib.Path)
p.add_argument('release_tag')
p.add_argument('output', type=pathlib.Path)
a = p.parse_args()
d = json.loads(a.reference.read_text())
d['id'] = 'x64-crossover26.3-memoryfix-r1'
d['displayName'] = 'Wine 11.0 macOS - WoW64 memory fixes r1 (experimental)'
d['notes'] = [
    'Experimental installer-focused fork by powermac84. Upstream memory fixes 1276773 and f4c5b04 are backported; the latter preserves CrossOver force_laa().',
    'The affected ntdll.so library was rebuilt from pinned CrossOver 26.3 sources plus Highball 0001-0024 (0013 held) and the two fixes. Every other Wine file is retained from the checksum-verified Highball CX r27 archive, including multimedia modules.',
    'Synthetic memory tests do not establish compatibility with any specific installer or game. This engine has its own identity and does not replace an existing engine.'
]
d.pop('verified', None)
c = d['components']['wine']
c['url'] = ('https://github.com/powermac84/wine-macos-memoryfix/releases/download/'
            + urllib.parse.quote(a.release_tag, safe='') + '/'
            + urllib.parse.quote(a.archive.name, safe=''))
c['sha256'] = hashlib.sha256(a.archive.read_bytes()).hexdigest()
c['size'] = a.archive.stat().st_size
c['version'] = 'wine-11.0 (CrossOver 26.3), WoW64 memoryfix-r1'
c['note'] = 'Community experimental engine assembled from the verified Highball CX r27 Wine archive with only the source-rebuilt ntdll.so replaced. Includes Wine 1276773 and f4c5b04. Source, selected patches and build recipe are in the matching release source archive. This is not the CrossOver product.'
a.output.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print(a.output)
