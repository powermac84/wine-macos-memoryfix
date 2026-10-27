# Sikarugir source-level routing check

This standalone harness contains the exact proposed `set_large_address_space()` function adapted to Sikarugir Wine master `840a939ee526137639665ff5f587224d6a36403f`. Its platform calls are mocked. It checks 30 combinations of machine, LAA state and environment value; it does not build Wine or validate a Sikarugir engine at runtime.

```sh
clang -std=c11 -Wall -Wextra -Werror function-routing-test.c -o function-routing-test
./function-routing-test
```

The runtime comparisons and bounded actual installer test apply to the separate CrossOver-derived Highball build. See [the proposal](../../docs/SIKARUGIR.md) for its scope and remaining validation.
