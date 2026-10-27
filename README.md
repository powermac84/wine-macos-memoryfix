<p align="center"><strong>WINE · macOS · APPLE SILICON</strong></p>

<h1 align="center">Get past the stall.</h1>

<p align="center"><strong>MEMORYFIX</strong><br>
A focused Wine build for FitGirl / FreeArc installers that freeze while unpacking.</p>

<p align="center"><img src="docs/assets/memoryfix-hero.png" width="100%" alt="Original 3D artwork: a graphite sports car above a night city, with pink and cyan light trails"></p>

<p align="center">
<a href="https://github.com/powermac84/wine-macos-memoryfix/releases/tag/macos-memoryfix-r2"><img src="docs/assets/download-r2.svg" width="202" height="46" alt="Download experimental r2"></a>
&nbsp;
<a href="docs/INSTALL.md"><img src="docs/assets/quickstart.svg" width="202" height="46" alt="Highball quickstart"></a>
</p>

<p align="center"><sub>Original generated artwork · illustrative, not a game screenshot</sub></p>

## FitGirl installers. A way forward on Mac.

MemoryFix clears a known FreeArc memory-probe loop that can leave a FitGirl installer stuck at **0.7%** with a busy CPU and no file progress. The r2 build has passed that stage under **Highball** on Apple silicon.

The same source fix should be portable to **CrossOver** and **Porting Kit / Sikarugir** through compatible Wine engine builds. Those integrations remain untested.

<table>
<tr>
<td width="33%" align="center"><strong>19 / 19</strong><br>helper files unpacked</td>
<td width="33%" align="center"><strong>102 MB</strong><br>written in the bounded installer test</td>
<td width="33%" align="center"><strong>24 / 24</strong><br>runtime comparison cases passed</td>
</tr>
</table>

**Verified: the previously blocked installer stage. Full installation and game launch are still unverified.**

## Choose your route

| App | Status | What to use |
|---|---|---|
| **Highball** | Installer stall cleared in the actual test | [Download r2](https://github.com/powermac84/wine-macos-memoryfix/releases/tag/macos-memoryfix-r2) · [Quickstart](docs/INSTALL.md) |
| **CrossOver** | Source-level portability expected; untested | A compatible engine build with the patch |
| **Porting Kit / Sikarugir** | Source-level portability expected; untested | [Sikarugir proposal](docs/SIKARUGIR.md) |

The downloadable package is built for Highball. CrossOver and Porting Kit need their own compatible engine integration.

## One small override

```text
WINE_LARGE_ADDRESS_AWARE=0
```

The r2 Highball manifest enables it automatically. It keeps automatic 32-bit allocations in the lower 2 GiB, avoiding an integer overflow in the decoder's memory check. **It is not a physical RAM cap.** Native 64-bit allocation behavior stays unchanged.

[How the fix works](README-MEMORYFIX-R2.md) · [Build from source](README-NTDLL.md) · [Patch 0030](patches/0030-ntdll-honor-explicit-large-address-aware-disable.patch) · [Test records](tests/laa-override/)

---

Independent community work, built on **Wine**, the published **CodeWeavers** LGPL sources and **Highball's** engine recipe. No game files or decoder DLLs are included. [Licences and credits](NOTICE.md) · [Original engine documentation](docs/UPSTREAM-ENGINE.md)
