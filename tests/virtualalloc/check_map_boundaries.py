#!/usr/bin/env python3
"""Compile the actual allocator search function with a deterministic view tree.

No real mmap is performed. Every attempted host mapping is refused, forcing
iteration from an in-range view to its out-of-range predecessor/successor.
The observable invariant is that try_map_free_area never receives bounds
outside the caller's requested [base,end) range.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def extract_function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[start:i+1]
    raise ValueError('unterminated function ' + signature)


PRELUDE = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#define min(a,b) ((a) < (b) ? (a) : (b))
#define max(a,b) ((a) > (b) ? (a) : (b))
#define ROUND_ADDR(addr,mask) ((void *)((uintptr_t)(addr) & ~(uintptr_t)(mask)))
#define ERR(...) ((void)0)
struct wine_rb_entry { struct wine_rb_entry *left, *right, *parent; };
struct file_view { struct wine_rb_entry entry; void *base; size_t size; };
struct { struct wine_rb_entry *root; } views_tree;
#define WINE_RB_ENTRY_VALUE(ptr,type,field) ((type *)((char *)(ptr) - offsetof(type,field)))
static struct wine_rb_entry *rb_next(struct wine_rb_entry *p)
{
    struct wine_rb_entry *parent;
    if (p->right) { p=p->right; while (p->left) p=p->left; return p; }
    while ((parent=p->parent) && p==parent->right) p=parent;
    return parent;
}
static struct wine_rb_entry *rb_prev(struct wine_rb_entry *p)
{
    struct wine_rb_entry *parent;
    if (p->left) { p=p->left; while (p->right) p=p->right; return p; }
    while ((parent=p->parent) && p==parent->left) p=parent;
    return parent;
}
static uintptr_t expected_low, expected_high;
static unsigned int calls, violations;
static void *try_map_free_area(void *base,void *end,ptrdiff_t step,
                               void *start,size_t size,int unix_prot)
{
    (void)step; (void)start; (void)size; (void)unix_prot;
    calls++;
    if ((uintptr_t)base < expected_low || (uintptr_t)end > expected_high)
    {
        fprintf(stderr,"OUTSIDE REQUEST: call [%p,%p), requested [0x%lx,0x%lx)\n",
                base,end,(unsigned long)expected_low,(unsigned long)expected_high);
        violations++;
    }
    /* Emulate a host whose candidate holes are all occupied: keep searching. */
    return NULL;
}
'''

MAIN = r'''
int main(void)
{
    struct file_view low={0},middle={0},high={0};
    unsigned int before, total_violations=0;
    void *result;
    low.base=(void *)0x80000; low.size=0x10000;
    middle.base=(void *)0x180000; middle.size=0x10000;
    high.base=(void *)0x280000; high.size=0x10000;
    middle.entry.left=&low.entry; middle.entry.right=&high.entry;
    low.entry.parent=high.entry.parent=&middle.entry;
    views_tree.root=&middle.entry;
    expected_low=0x100000; expected_high=0x200000;
    for (int direction=0; direction<2; direction++)
    {
        calls=violations=0;
        before=total_violations;
        result=map_free_area((void *)expected_low,(void *)expected_high,
                             0x10000,direction,0,0xffff);
        if (result != NULL || calls != 2)
        {
            fprintf(stderr,"HARNESS ERROR direction=%d calls=%u result=%p\n",direction,calls,result);
            return 2;
        }
        total_violations += violations;
        printf("%s calls=%u boundary_violations=%u\n",
               direction?"top-down":"bottom-up",calls,total_violations-before);
    }
    return total_violations ? 1 : 0;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Wine dlls/ntdll/unix/virtual.c')
    parser.add_argument('--cc',default='cc')
    args=parser.parse_args()
    source=args.source.read_text()
    functions='\n\n'.join(extract_function(source,s) for s in [
        'static struct wine_rb_entry *find_view_inside_range(',
        'static void *map_free_area('])
    with tempfile.TemporaryDirectory(prefix='map-free-area-') as work:
        work=Path(work)
        c=work/'test.c'; exe=work/'test'
        c.write_text(PRELUDE+'\n'+functions+'\n'+MAIN)
        subprocess.run([args.cc,'-std=c11','-O0','-Wall','-Wextra','-Werror','-Wno-sign-compare',str(c),'-o',str(exe)],check=True)
        return subprocess.run([str(exe)],timeout=5).returncode


if __name__=='__main__':
    raise SystemExit(main())
