# Proposed for Sikarugir

**[Draft pull request #4 → Sikarugir-App/wine](https://github.com/Sikarugir-App/wine/pull/4)**

[Single proposed commit](https://github.com/powermac84/wine-sikarugir-memoryfix/commit/a1d5efe7674676ba48dce8794626d2988fb7c4ee) · [Download the reviewable patch](sikarugir-laa-override.patch)

The proposal adapts the r2 explicit `WINE_LARGE_ADDRESS_AWARE=0` option to Sikarugir's current public Wine source. It changes one file, preserves default behavior, and leaves native 64-bit images on their existing path.

The two r1 Wine commits are already included in Sikarugir's current master, so they are not proposed again.

## What is checked

The patch applies with zero fuzz to Wine master `840a939ee526137639665ff5f587224d6a36403f` (11.20). A harness compiled from the exact proposed function passes 30 source-level routing checks; the [test source and instructions](../tests/sikarugir/) are included here.

The equivalent option has passed actual runtime comparisons and the bounded installer test in the separate Highball engine. This Sikarugir adaptation has not yet been built or run as a complete engine.

## What remains

The draft asks maintainers to confirm the right engine integration branch and validate a native Sikarugir build before release. The published Sikarugir engine catalog does not establish a source mapping to this master branch. Porting Kit integration therefore remains a candidate, not a verified installation route.
