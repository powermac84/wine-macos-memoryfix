# macOS installer compatibility: r2

This experimental release adds a local, opt-in workaround for a 32-bit FreeArc arithmetic overflow. It is not an upstream Wine commit. The r1 Wine backports remain included.

## Observed failure

The supplied installer stayed at its first tool file with a busy CPU core. Its internal `setup.tmp` is 32-bit and LARGE_ADDRESS_AWARE, even though the outer setup.exe is not. The bundled unarc.dll searches for the largest reservable block using `(low + high) / 2` with 32-bit unsigned arithmetic. When its first request of 0x7fffffff bytes succeeds, the midpoint sum wraps and eventually repeats zero-byte requests forever.

The same arithmetic appears in [FreeArc Environment.cpp](https://github.com/phyxolog/FreeArc/blob/721118f7e3e506cfde32f8febeddf274b3a83d75/Environment.cpp#L222-L230). Disassembly of the supplied decoder confirmed it; a bounded standalone reproduction confirmed the failure and workaround.

## Workaround and scope

Patch 0030 honors the exact environment value `WINE_LARGE_ADDRESS_AWARE=0`, including when the process PE header has its LAA bit set. This selects the existing 2 GiB automatic allocation search range for WoW64. It prevents that initial near-2-GiB reservation and the overflow. It is not a physical RAM quota or a prohibition on every explicit fixed-address reservation above 2 GiB.

The library preserves existing behavior when the variable is absent, 1, or any value other than exact 0. Native 64-bit allocation behavior is unchanged. The r2 Highball manifest enables 0 by default for installer use. A bottle override of `WINE_LARGE_ADDRESS_AWARE=1` restores the previous LAA behavior for that bottle.

## Validation

- Final signed ntdll.so SHA-256: `76287b49872d6205d5a784ad2b7e8564fbb4ade31ffa6d6c2b2d90b241ebfa4a`.
- Twelve runtime cases on r1 and twelve on the final library passed: x86 LAA, x86 non-LAA and x64, each with unset/0/1/00. Only the intended LAA x86 exact-0 case changed. The test source and result records are in `tests/laa-override/`.
- The unmodified original installer was run in a temporary prefix and a fresh destination using the final library. All 19 helper files (13,993,168 bytes), including the formerly empty first DLL, were extracted. The installer then wrote additional installation data. The bounded test was deliberately stopped after 21.7 seconds at 102,235,637 destination bytes.
- Complete installation, reconstruction of all game files and game launch have not been tested.

## Build and packaging

Follow [README-NTDLL.md](README-NTDLL.md). The selected source series is Highball 0001-0024 excluding held 0013, then 0028, 0029 and 0030. The matching source archive includes the original SHA-pinned LGPL source, every selected patch, configuration and build metadata, and the build script.

The engine is composed from the SHA-256-verified original Highball CX r27 Wine archive. Only `engine/lib/wine/x86_64-unix/ntdll.so` is replaced. Other Wine files, runtime/framework components and renderers are preserved. No game archives, game decoders, private user logs or optional Apple runtime binaries are redistributed in this engine archive.
