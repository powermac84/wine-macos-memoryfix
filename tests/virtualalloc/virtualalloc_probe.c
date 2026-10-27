/* SPDX-License-Identifier: MIT
 * Exercise virtual address reservation without committing gigabytes of RAM.
 * Run in an isolated WINEPREFIX with an external timeout (see README.md).
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned int failures;
static unsigned int successful_large_reservations;
static int is_32bit;
static int large_address_aware;

static void fail(const char *what)
{
    ++failures;
    printf("FAIL: %s (GetLastError=%lu)\n", what, (unsigned long)GetLastError());
    fflush(stdout);
}

static void check_span(const void *base, SIZE_T size, const char *label)
{
    uint64_t lo = (uint64_t)(uintptr_t)base;
    uint64_t hi = lo + (uint64_t)size;
    if (!size || hi <= lo) fail("zero-sized or overflowing address span");
    if (is_32bit && hi > UINT64_C(0x100000000))
        fail("32-bit reservation extends beyond 4 GiB");
    if (is_32bit && !large_address_aware && hi > UINT64_C(0x80000000))
        fail("non-LAA 32-bit reservation extends beyond 2 GiB");
    printf("  %s base=0x%llx size=0x%llx end-exclusive=0x%llx\n", label,
           (unsigned long long)lo, (unsigned long long)size, (unsigned long long)hi);
}

static void small_top_down(unsigned int sequence)
{
    volatile DWORD *p = VirtualAlloc(NULL, 0x1000, MEM_RESERVE | MEM_COMMIT | MEM_TOP_DOWN,
                                     PAGE_READWRITE);
    if (!p) { fail("small top-down allocation after reservation probe"); return; }
    check_span((const void *)p, 0x1000, "top-down committed sentinel");
    *p = 0xa5a50000u ^ sequence;
    if (*p != (0xa5a50000u ^ sequence)) fail("sentinel readback");
    if (!VirtualFree((void *)p, 0, MEM_RELEASE)) fail("release sentinel");
}

static void reservation(SIZE_T size, DWORD mode, unsigned int sequence)
{
    MEMORY_BASIC_INFORMATION mbi;
    void *p;
    DWORD error;
    uint64_t requested = (uint64_t)size;
    uint64_t rounded = (requested + UINT64_C(0xfff)) & ~UINT64_C(0xfff);
    printf("BEGIN sequence=%u reserve=0x%llx mode=%s\n", sequence,
           (unsigned long long)requested, mode ? "top-down" : "bottom-up");
    fflush(stdout); /* The final BEGIN identifies a hanging call. */
    SetLastError(0);
    p = VirtualAlloc(NULL, size, MEM_RESERVE | mode, PAGE_READWRITE);
    error = GetLastError();
    if (!p)
    {
        /* Address space can be fragmented; a failed huge allocation is valid. */
        printf("  reservation refused error=%lu\n", (unsigned long)error);
    }
    else
    {
        ++successful_large_reservations;
        check_span(p, size, "requested span");
        if (VirtualQuery(p, &mbi, sizeof(mbi)) != sizeof(mbi)) fail("VirtualQuery reservation");
        else
        {
            check_span(mbi.BaseAddress, mbi.RegionSize, "queried span");
            if (mbi.State != MEM_RESERVE) fail("reservation unexpectedly committed");
            if (mbi.AllocationBase != p || mbi.BaseAddress != p) fail("wrong queried allocation base");
            if ((uint64_t)mbi.RegionSize < rounded) fail("queried region shorter than rounded request");
        }
        if (!VirtualFree(p, 0, MEM_RELEASE)) fail("release large reservation");
    }
    small_top_down(sequence);
    printf("END sequence=%u\n", sequence);
    fflush(stdout);
}

int main(int argc, char **argv)
{
    static const uint32_t sizes[] = {0x10000000u, 0x7fff0000u, 0x7fffffffu, 0x80000000u,
                                    0x80010000u, 0xbfff0000u, 0xffff0000u};
    unsigned int loops = 4, i, j, sequence = 0;
    BOOL wow64 = FALSE;
    int require_wow64 = 0;
    const IMAGE_DOS_HEADER *dos = (const IMAGE_DOS_HEADER *)GetModuleHandleW(NULL);
    const IMAGE_NT_HEADERS *nt = (const IMAGE_NT_HEADERS *)((const char *)dos + dos->e_lfanew);
    for (i = 1; i < (unsigned int)argc; ++i)
    {
        if (!strcmp(argv[i], "--require-wow64")) require_wow64 = 1;
        else if (!strcmp(argv[i], "--iterations") && i + 1 < (unsigned int)argc)
        {
            char *end;
            unsigned long n = strtoul(argv[++i], &end, 10);
            if (*end || !n || n > 32) { fprintf(stderr, "iterations must be 1..32\n"); return 2; }
            loops = (unsigned int)n;
        }
        else { fprintf(stderr, "usage: probe.exe [--require-wow64] [--iterations 1..32]\n"); return 2; }
    }
    is_32bit = sizeof(void *) == 4;
    large_address_aware = !!(nt->FileHeader.Characteristics & IMAGE_FILE_LARGE_ADDRESS_AWARE);
    if (!IsWow64Process(GetCurrentProcess(), &wow64)) fail("IsWow64Process");
    printf("pointer_bits=%u LAA=%d wow64=%u iterations=%u\n", (unsigned int)(sizeof(void *) * 8),
           large_address_aware, (unsigned int)wow64, loops);
    fflush(stdout);
    if (require_wow64 && (!is_32bit || !wow64))
    {
        fprintf(stderr, "SKIP: requires a 32-bit process under WoW64\n"); return 77;
    }
    for (j = 0; j < loops; ++j)
        for (i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i)
        {
            reservation((SIZE_T)sizes[i], 0, ++sequence);
            reservation((SIZE_T)sizes[i], MEM_TOP_DOWN, ++sequence);
        }
    printf("RESULT failures=%u successful_large_reservations=%u probes=%u\n",
           failures, successful_large_reservations, sequence);
    /* Guard against passing solely because every reservation was rejected. */
    if (!successful_large_reservations)
    {
        fprintf(stderr, "INCONCLUSIVE: no large reservation succeeded; inspect address-space pressure\n");
        return failures ? 1 : 77;
    }
    return failures ? 1 : 0;
}
