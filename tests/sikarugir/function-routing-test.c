#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
typedef int BOOL;
#define FALSE 0
#define IMAGE_FILE_MACHINE_I386 0x14c
#define IMAGE_FILE_MACHINE_AMD64 0x8664
#define IMAGE_FILE_LARGE_ADDRESS_AWARE 0x20
#define AREA_BLOCKED 7
#define min(a,b) ((a)<(b)?(a):(b))
static struct { unsigned short Machine,ImageCharacteristics; } main_image_info;
static BOOL is_win64;
static uintptr_t limit_2g=0x80000000ULL,limit_4g=0x100000000ULL,user_space_wow_limit;
static void *address_space_start,*main_module,*host_addr_space_limit,*address_space_limit;
static void *user_space_limit,*working_set_limit;
static int blocked,reserved,mapped;
static uintptr_t blocked_base,blocked_size,reserved_base;
static int is_machine_64bit(unsigned short m) { return m==IMAGE_FILE_MACHINE_AMD64; }
static void map_fixed_area(void *p,uintptr_t s,int prot) { (void)p;(void)s;(void)prot;mapped++; }
static void set_mem_area_state(void *p,uintptr_t s,int state) { if(state!=AREA_BLOCKED)abort();blocked++;blocked_base=(uintptr_t)p;blocked_size=s; }
static void reserve_area(void *p,void *e) { (void)e;reserved++;reserved_base=(uintptr_t)p; }

static void set_large_address_space(void)
{
    const char *large_address_space_override;
    BOOL large_address_aware = main_image_info.ImageCharacteristics & IMAGE_FILE_LARGE_ADDRESS_AWARE;

    if (is_machine_64bit( main_image_info.Machine )) return;

    /* Compatibility override for 32-bit code with overflowing memory-size probes. */
    large_address_space_override = getenv( "WINE_LARGE_ADDRESS_AWARE" );
    if (large_address_space_override && !strcmp( large_address_space_override, "0" ))
        large_address_aware = FALSE;

    if (main_image_info.Machine == IMAGE_FILE_MACHINE_I386)
    {
        /* reserve the DOS area, and make it accessible (except the low 64K)
         * to hide bugs in broken apps like Excel 2003 */
        char *end, *start = address_space_start;  /* low 64K */
        address_space_start = (void *)0x110000;
        end = min( address_space_start, main_module );
        if (end > start) map_fixed_area( start, end - start, PROT_READ | PROT_WRITE );
    }

    if (is_win64)
    {
        if (large_address_aware)
        {
            user_space_wow_limit = limit_4g - 1;
            /* block a bit of top memory: some apps break if the entire high 2G is available */
            set_mem_area_state( (void *)0xfffe0000, 0x20000, AREA_BLOCKED );
        }
        else
        {
            user_space_wow_limit = limit_2g - 1;
            set_mem_area_state( (void *)0x7fff0000, 0x10000, AREA_BLOCKED );
        }
    }
    else if (!large_address_aware)
    {
        reserve_area( (void *)limit_2g, host_addr_space_limit );
        return;
    }
    user_space_limit = working_set_limit = address_space_limit;
}



int main(void)
{
    const char *modes[]={NULL,"0","1","00",""};
    int cases=0;
    for(int arch=0;arch<3;arch++) for(int laa=0;laa<2;laa++) for(int mode=0;mode<5;mode++)
    {
        int inactive=!laa || mode==1;
        if(modes[mode])setenv("WINE_LARGE_ADDRESS_AWARE",modes[mode],1);else unsetenv("WINE_LARGE_ADDRESS_AWARE");
        main_image_info.Machine=arch==2?IMAGE_FILE_MACHINE_AMD64:IMAGE_FILE_MACHINE_I386;
        main_image_info.ImageCharacteristics=laa?IMAGE_FILE_LARGE_ADDRESS_AWARE:0;
        is_win64=arch!=1;
        address_space_start=(void*)0x10000;main_module=(void*)0x400000;
        host_addr_space_limit=(void*)0x100000000ULL;address_space_limit=(void*)0x200000000ULL;
        user_space_wow_limit=123;user_space_limit=(void*)456;working_set_limit=(void*)789;
        blocked=reserved=mapped=0;blocked_base=blocked_size=reserved_base=0;
        set_large_address_space();
        if(arch==2) { if(blocked||reserved||mapped||user_space_wow_limit!=123||user_space_limit!=(void*)456||working_set_limit!=(void*)789)return 1; }
        else if(arch==0) {
            if(blocked!=1||reserved||mapped!=1||user_space_wow_limit!=(inactive?limit_2g-1:limit_4g-1)||blocked_base!=(inactive?0x7fff0000:0xfffe0000)||blocked_size!=(inactive?0x10000:0x20000)||user_space_limit!=address_space_limit||working_set_limit!=address_space_limit)return 2;
        } else {
            if(blocked||mapped!=1||reserved!=inactive)return 3;
            if(inactive&&(reserved_base!=limit_2g||user_space_limit!=(void*)456||working_set_limit!=(void*)789))return 4;
            if(!inactive&&(user_space_limit!=address_space_limit||working_set_limit!=address_space_limit))return 5;
        }
        cases++;
    }
    printf("PASS %d branch cases from the exact proposed Sikarugir function; not a full Wine build or runtime test\n",cases);
    return 0;
}
