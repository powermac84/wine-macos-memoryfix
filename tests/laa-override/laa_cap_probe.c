#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

int main(void)
{
    SYSTEM_INFO si;
    char setting[16];
    void *big, *high;
    DWORD big_error, high_error;
    GetSystemInfo(&si);
    if (!GetEnvironmentVariableA("WINE_LARGE_ADDRESS_AWARE", setting, sizeof(setting)))
        lstrcpyA(setting, "unset");
    SetLastError(0);
    big = VirtualAlloc(NULL, (SIZE_T)0x7fffffff, MEM_RESERVE, PAGE_READWRITE);
    big_error = GetLastError();
    if (big) VirtualFree(big, 0, MEM_RELEASE);
    SetLastError(0);
    high = VirtualAlloc((void *)(ULONG_PTR)0x90000000, 65536, MEM_RESERVE, PAGE_READWRITE);
    high_error = GetLastError();
    if (high) VirtualFree(high, 0, MEM_RELEASE);
    printf("RESULT ptrbits=%u setting=%s maxapp=%p big=%p bigerror=%lu high=%p higherror=%lu\n",
           (unsigned)(sizeof(void *)*8), setting, si.lpMaximumApplicationAddress,
           big, big_error, high, high_error);
    fflush(stdout);
    return 0;
}
