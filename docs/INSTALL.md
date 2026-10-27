# Install r2 in Highball

Use a dedicated test environment. The published build was tested on Apple silicon under Rosetta 2; its manifest requires macOS 14 or later.

## 1. Get the files

Download [highball-memoryfix-r2.json](https://github.com/powermac84/wine-macos-memoryfix/releases/download/macos-memoryfix-r2/highball-memoryfix-r2.json) and [SHA256SUMS](https://github.com/powermac84/wine-macos-memoryfix/releases/download/macos-memoryfix-r2/SHA256SUMS) into the same folder.

You also need the official Highball command-line tool. An unmodified Apple-silicon build is available in our [CLI archive](https://github.com/powermac84/wine-macos-memoryfix/releases/download/macos-memoryfix-r1/highball-cli-arm64-cddc6d1.tar.gz), with its [checksum](https://github.com/powermac84/wine-macos-memoryfix/releases/download/macos-memoryfix-r1/highball-cli-arm64-cddc6d1.tar.gz.sha256) and [matching source](https://github.com/powermac84/wine-macos-memoryfix/releases/download/macos-memoryfix-r1/highball-cli-source-cddc6d1.tar.gz). It is built from Highball commit `cddc6d1`; it does not ship inside the Wine engine archive. Other hosts can build the CLI from the official Highball sources.

Extract the CLI archive. In Terminal, open the download folder and verify the two small files before installation:

```sh
shasum -a 256 -c highball-cli-arm64-cddc6d1.tar.gz.sha256
sed -n '/  highball-memoryfix-r2.json$/p' SHA256SUMS | shasum -a 256 -c -
```

## 2. Install the engine and create an environment

The commands below use the Apple-silicon CLI archive directly. The engine installer downloads and verifies the Wine package and its required components.

```sh
HBCLI="$PWD/highball-cli-arm64-cddc6d1/highball"
"$HBCLI" engine install "$PWD/highball-memoryfix-r2.json"
"$HBCLI" bottle create FitGirl --engine x64-crossover26.3-memoryfix-r2 --renderer wined3d
"$HBCLI" bottle set FitGirl winver win10
"$HBCLI" bottle set FitGirl sync none
```

The manifest supplies `WINE_LARGE_ADDRESS_AWARE=0`. This is the compatibility setting used to clear the memory-probe loop. The installer's own 4 GB option controls something else.

## 3. Add the installer to Highball

Replace the example path with your setup.exe path. Keep the matching .bin files beside it, then run:

```sh
"$HBCLI" pin add FitGirl "FitGirl installer" "/absolute/path/to/setup.exe"
```

Reopen Highball to refresh its library, then launch **FitGirl installer**. Choose a destination inside this environment's C: drive, as in the bounded test. Check actual file growth when judging progress.

## Existing test environment

To use r2 in an existing environment, substitute its name for `FitGirl`:

```sh
"$HBCLI" bottle kill FitGirl
"$HBCLI" bottle set FitGirl engine x64-crossover26.3-memoryfix-r2
"$HBCLI" bottle set FitGirl env WINE_LARGE_ADDRESS_AWARE=0
"$HBCLI" bottle repair FitGirl
```

To restore the previous LAA behavior while keeping this engine, set `WINE_LARGE_ADDRESS_AWARE=1` for that environment. The override changes automatic 32-bit address search; it is not a hard RAM quota. The earlier r1 engine can also remain installed for comparison.

## Compatibility boundary

r2 was tested through the formerly blocked helper stage and subsequent file writes. Full installation, final reconstruction and game launch remain unverified. CrossOver and Porting Kit require builds adapted to their own engines; the Highball archive is packaged specifically for Highball.
