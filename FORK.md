# macOS Wine virtual-memory backport

Release **macos-memoryfix-r2** adds an opt-in FreeArc overflow workaround and has passed the formerly stuck installer stage in a bounded actual run. See [r2 behavior, validation and limits](README-MEMORYFIX-R2.md). This local workaround is separate from the two upstream r1 commits.

Release **macos-memoryfix-r1** uses the targeted build in [README-NTDLL.md](README-NTDLL.md): only `ntdll.so` is replaced in the SHA-256-verified Highball CX r27 Wine archive. All other modules, including GStreamer, are retained. The full-build workflow documented below is an additional, separately produced variant.

Experimental fork of `gauthierpiarrette/highball-engine`, based on upstream
commit `e497c41d16a1ebfd22d8fdd307ea73439c6df7ee`. It builds an x86_64 macOS
Wine engine from the SHA-256-pinned CrossOver 26.3 LGPL source. On Apple silicon
this engine runs through Rosetta 2.

## Changes

- `0028`: Wine commit `1276773f69890b63113d23647258f16f2957996e`, by
  Alexandre Julliard: keep `map_free_area()` searches inside the caller's limits.
- `0029`: Wine commit `f4c5b04148db5fc4e5265beec461d3b7d9f4a789`, by
  Alexandre Julliard: reserve a small high-address range for WoW64 top-down
  allocations. Adapted to retain CrossOver's existing `force_laa()` condition.

The Rosetta DEP patch `0013` stays held, matching Highball CX r27.
GStreamer is disabled for this installer-focused build. CoreAudio, fonts, TLS,
SDL and MoltenVK host-library dependencies are bundled and relocated into the
engine, so an Intel Homebrew installation is not required on the target Mac.

These are the upstream fixes, not a blanket 2 GiB allocation rejection and not
a physical RAM cap. The fork does not change Highball's installed environments.
No game data, user logs, or proprietary Apple D3DMetal binaries are included.

## Build and release

In Actions, enable workflows for this fork and manually run
**build-memoryfix-engine**, with `ref_note=wow64-memoryfix-r1`.
Set `publish_release=true` to publish an experimental prerelease after the
build and synthetic tests succeed. The build uses GitHub's Intel macOS runner.
No push automatically triggers the expensive engine build.

The release contains the engine archive, SHA-256 checksums, and corresponding
source (original pinned source archive, patch series, notices and probe tests).
The engine archive records the fork commit and test logs. Use the source
archive together with this tagged repository's build recipe to reproduce it.

## Validation and limits

All patches must apply with zero fuzz. A deterministic test compiles the actual
Wine allocation-search functions with a controlled mapping tree: the pinned
baseline must fail and the patched source must pass. Runtime tests use 32-bit
LAA, 32-bit non-LAA and 64-bit Windows executables in fresh prefixes, with
timeouts. They reserve large virtual regions but commit only 4 KiB sentinels.

Passing these tests does not establish that a specific installer or game works.
The repack's source integrity and a full installer run must be checked separately.
This is a community Wine build from published LGPL sources, not the CrossOver
product and not a CodeWeavers-supported release.

See [the original project README](README.md), [patch details](patches/README.md),
and [probe instructions](tests/virtualalloc/README.md).
