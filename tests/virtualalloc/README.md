# Virtual address reservation regression probe

This is a synthetic Wine allocator regression probe, not proof that a particular
repack installer succeeds. It reserves address space around the 2 GiB boundary
without committing those large regions; only one 4 KiB sentinel is committed at
a time. A 256 MiB control reservation is included because a healthy patched 32-bit
process may legitimately reject every contiguous 2 GiB request. Four iterations
perform 56 reserve/free operations in both
allocation directions. Each successful reservation is queried and must have a
non-overflowing span; all 32-bit spans must end at or below 4 GiB and non-LAA
32-bit spans at or below 2 GiB. A small committed top-down allocation and sentinel
readback follow each probe. Normal allocation failure is acceptable: this test
must not demand a contiguous 2 GiB mapping in a fragmented process.

Compile with MinGW-w64 (GCC or clang targeting the matching Windows ABI):

```sh
i686-w64-mingw32-gcc -O2 -Wall -Wextra -Werror -Wl,--large-address-aware virtualalloc_probe.c -o virtualalloc-x86-laa.exe
i686-w64-mingw32-gcc -O2 -Wall -Wextra -Werror virtualalloc_probe.c -o virtualalloc-x86-nonlaa.exe
x86_64-w64-mingw32-gcc -O2 -Wall -Wextra -Werror virtualalloc_probe.c -o virtualalloc-x64.exe
```

With an isolated disposable WINEPREFIX, run each under a host-side timeout.
The x86 LAA case must pass `--require-wow64`. Use the exact same EXEs and
arguments on baseline and patched engines, with fresh isolated prefixes:

```sh
WINEPREFIX=/absolute/path/to/disposable-prefix /path/to/wine virtualalloc-x86-laa.exe --require-wow64
WINEPREFIX=/absolute/path/to/disposable-prefix /path/to/wine virtualalloc-x86-nonlaa.exe --require-wow64
WINEPREFIX=/absolute/path/to/disposable-prefix /path/to/wine virtualalloc-x64.exe
```

**Apply a 60 second host timeout per invocation.** A Python caller can use
`subprocess.run(command, timeout=60, env=...)`. On timeout terminate the process
and run the matching `wineserver -k` with the same disposable WINEPREFIX; do not
kill unrelated Wine environments. Logging flushes before every VirtualAlloc,
so the last BEGIN identifies a call that does not return. Never replace this
with a giant committed allocation or a system-wide memory limit.

Exit 0 means no detected violations. Exit 1 means a check failed. Exit 2 means
invalid arguments. Exit 77 means the run was inconclusive (wrong process mode,
or none of the large reservations succeeded). It must not be reported as a pass.
The baseline may already pass this synthetic probe; that does not invalidate the
patches or prove their necessity. The allocator's internal tree traversal bug
also depends on the live mapping layout and may need a lower-level unit harness.
Run the real installer separately after the synthetic checks.

Backport review note: CrossOver 26.3 computes `large_address_space_active` using
both the executable's LAA flag and `force_laa()`. Preserve that condition while
porting f4c5b04; its body sets `user_space_wow_limit = limit_4g - 1`, calls
`reserve_area((void *)0xfff00000, (void *)0xffff0000)`, and retains the 2 GiB branch.
Do not add a blanket 2 GiB allocation rejection: that is the older workaround,
not these upstream fixes. `reserve_area` already implements Mach VM reservation
on macOS, so the new call does not require a Linux API.
