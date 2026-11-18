# Installation

> **There is no release to install yet.** The tool is still being built. A command-line version
> can be run from source today (see "Running from source"). The packaged program with overlay
> and settings window does not exist yet, and the sections marked *planned* describe how
> installing it will work.

## Requirements

| | |
|---|---|
| Operating system | Windows 10 or Windows 11, 64-bit |
| Game | ELDEN RING NIGHTREIGN, in **windowed** or **borderless windowed** mode |
| Game language | English, 简体中文 or 繁體中文 (for reading boss names) |
| Disk space | about 200 MB (*planned*, to be confirmed with the first build) |
| HDR | off is recommended; colour detection may be less reliable with HDR on |

Exclusive fullscreen is not supported: an overlay cannot draw over it, and screen capture may
return a black image.

## Install the release (*planned*)

1. Open the repository's **Releases** page and download the latest
   `nightreign-boss-timer-<version>-windows.zip`.
2. Extract the whole ZIP to a folder you can write to, for example `C:\Tools\nightreign-boss-timer`.
   Keep all the files together. Do not run it from inside the ZIP.
3. Run `nightreign-boss-timer.exe`.
4. Windows may show a SmartScreen warning, because the program is not signed. Choose
   **More info**, then **Run anyway**. Only do this for a ZIP downloaded from this repository's
   Releases page.
5. The first-run setup opens. Continue with the [user guide](USER_GUIDE.md#first-run-setup).

The release contains its own Python runtime. Nothing else needs to be installed.

## Update (*planned*)

1. Quit the tool from its tray icon.
2. Download the new ZIP and extract it over the old folder, or into a new folder and delete the
   old one.

Your settings and your records are kept outside the program folder, so updating or deleting the
program does not touch them:

| What | Where |
|---|---|
| Settings (regions, hotkeys, tables) | `%APPDATA%\nightreign-boss-timer\` |
| Records | `Documents\nightreign-boss-timer\records.csv`, unless you chose another folder |

## Uninstall (*planned*)

1. Quit the tool from its tray icon.
2. Delete the program folder.
3. To remove everything, also delete `%APPDATA%\nightreign-boss-timer\`. Delete the records
   folder only if you no longer want your fight history.

The tool installs no drivers and no services, and writes nothing to the game's folder.

## Running from source

This works today and is the only way to run the tool until there is a release.

1. Install [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).
2. Get the code and its dependencies:

   ```powershell
   git clone https://github.com/sunfish-LittleKight/nightreign-boss-timer.git
   cd nightreign-boss-timer
   uv sync --dev
   ```

3. Download the text recognition model used to read boss names (21 MB, once). It is checked
   against a known checksum and saved under `%LOCALAPPDATA%\nightreign-boss-timer\models`:

   ```powershell
   uv run python tools/fetch_model.py
   ```

   Without the model the tool still times fights, and records the boss as `unknown`.

4. Start the game in windowed or borderless windowed mode, then run the command-line version:

   ```powershell
   uv run python -m nightreign_boss_timer --table Arena
   ```

   It prints each finished fight and appends it to
   `Documents\nightreign-boss-timer\records.csv`. Stop it with Ctrl+C.

   Or run the version with the overlay and tray icon. Its tray menu switches the table, opens the records
   file, has **Calibrate regions** (see the [user guide](USER_GUIDE.md#first-run-setup)) and
   **Quit**:

   ```powershell
   uv run python -m nightreign_boss_timer.ui.app
   ```

| Option | Meaning | Default |
|---|---|---|
| `--table NAME` | table to save fights under | `Arena` |
| `--records PATH` | where to write the CSV | `Documents\nightreign-boss-timer\records.csv` |
| `--title TEXT` | title of the game window, if it is not found | `ELDEN RING NIGHTREIGN` |

The command-line version has no overlay, no settings window and no calibration screen of its
own. It uses the regions calibrated in the overlay version, and assumes a 16:9 game image until
then.

To measure what the tool costs on your PC, run this with the game open:

```powershell
uv run python tools/bench_capture.py
```

For developers, the checks are `uv run ruff check .` and `uv run pytest`. uv downloads the right
Python version on its own. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the workflow.

## Troubleshooting installation (*planned*)

| Problem | What to check |
|---|---|
| The program does not start | Extract the whole ZIP first. Check that antivirus did not remove files from the folder. |
| "Game not found" | Start the game first, or pick its window under Settings, Capture. |
| The overlay is not visible | Set the game to windowed or borderless windowed, not fullscreen. |
| Hotkeys do nothing | Another program may already use that shortcut. The Hotkeys page marks shortcuts that failed to register. |

## Safety

The tool only looks at screen pixels. It does not read game memory, inject code, or change game
files. No third-party tool can be guaranteed safe with anti-cheat software, so you use it at your
own risk.
