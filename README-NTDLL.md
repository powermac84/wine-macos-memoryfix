# Build the macOS x86_64 Wine allocator backport

This script rebuilds **only `ntdll.so`**, from the SHA-256-pinned original
CrossOver 26.3 source in `inputs.json`. It applies the exact Highball CX-r27
series, patches 0001–0024 excluding held patch 0013, then the upstream allocator
backports 0028 and 0029, followed by local compatibility patch 0030. No other Wine module is rebuilt or replaced.

Requirements: macOS, Xcode command-line tools/Apple clang, Bison >= 3, and a
macOS-hosted LLVM-MinGW toolchain providing `i686-w64-mingw32-gcc` and
`x86_64-w64-mingw32-gcc`. Apple Silicon also needs Rosetta 2. The successful
local run used LLVM-MinGW 20260922 UCRT and Bison 3.8.2; compiler/SDK versions
are recorded with each output. The script prefers Homebrew's keg-only Bison
when present and does not install tools or change shell configuration.

From the repository root:

```sh
scripts/build-ntdll-macos.sh \
  /absolute/path/to/llvm-mingw/bin \
  /private/tmp/ntdll-build-fresh \
  /private/tmp/ntdll-output \
  /absolute/path/to/crossover-sources-26.3.0.tar.gz
```

Omit the fourth argument to download the pinned source. The work directory
must not already contain a source or build tree. `JOBS=4` is the default.
The default preserves the exact tested build procedure and signs ad hoc
without stripping. `STRIP_NTDLL=1` additionally strips local/debug symbols;
that produces a different binary and should receive the same runtime tests.
The output includes the library, SHA-256, build logs, compiler/config metadata
and the applied patches' checksums. There is no user-engine installation step.

For a complete experimental engine, verify the original Highball engine
archive against its published SHA-256 **before extracting it into a fresh
staging directory**. Replace only
`engine/lib/wine/x86_64-unix/ntdll.so` with this output. Every other file should
remain byte-identical to the raw original archive; preserve file modes and
symlinks. Do not compose from an installed engine, which may contain optional
licensed components, local repair modifications or user-specific links.

Keep the public reference manifest's runtime/framework/renderer components,
changing only the Wine archive URL, size and SHA-256 plus the custom engine's
identity and notes. In particular, retaining the original Wine modules means
GStreamer remains supported through its existing public framework component.
The separately built `ntdll.so` uses only Apple system frameworks/libSystem
and does not replace or depend on the bundled GStreamer modules.

The exact local library was tested in a task-only APFS copy of CX-r27: x86 LAA,
x86 non-LAA and x64 probes each completed all 56 reservations with zero check
failures. This establishes ABI compatibility for those tests; it does not
establish that a particular repack installer succeeds. The composed raw-archive
engine should receive the same checks before publication, and the game
installer is a separate endpoint test.

For r2, see [the actual installer test and explicit LAA override scope](README-MEMORYFIX-R2.md). The release manifest enables `WINE_LARGE_ADDRESS_AWARE=0`; the library itself preserves prior behavior unless that exact value is supplied.
