# Installation

> **No release has been published yet.** The program can be built as a ready-to-run Windows
> folder today (see "Build the program yourself"), and the install steps below were followed
> with such a build. It has not been run against the real game yet.

## Requirements

| | |
|---|---|
| Operating system | Windows 10 or Windows 11, 64-bit. On Windows 10 older than version 2004 the overlay cannot be kept out of screen captures |
| Game | ELDEN RING NIGHTREIGN, in **windowed** or **borderless windowed** mode |
| Game language | English, 简体中文 or 繁體中文 (for reading boss names) |
| Disk space | about 180 MB (the download is about 75 MB) |
| Memory | about 200 MB while running |
| HDR | off is recommended; colour detection may be less reliable with HDR on |

Exclusive fullscreen is not supported: an overlay cannot draw over it, and screen capture may
return a black image.

## Install the release

1. Open the repository's **Releases** page and download the latest
   `nightreign-boss-timer-<version>-windows.zip`. Until the first release is published, build
   the program yourself (below), or download the `nightreign-boss-timer-windows` artifact
   of the latest **Build** run on the repository's **Actions** tab.
2. Extract the whole ZIP to a folder you can write to, for example `C:\Tools\nightreign-boss-timer`.
   Keep all the files together. Do not run it from inside the ZIP.
3. Run `nightreign-boss-timer.exe`. An icon appears in the system tray, near the clock. It may
   be behind the **^** arrow. The program has no other window until you click that icon.
4. Windows may show a SmartScreen warning, because the program is not signed. Choose
   **More info**, then **Run anyway**. Only do this for a ZIP downloaded from this repository's
   Releases page.
5. The first-run setup opens. Continue with the [user guide](USER_GUIDE.md#first-run-setup).

The release contains its own Python runtime and the text recognition model. Nothing else needs
to be installed, and nothing is downloaded when it runs.

The folder also holds `README.txt`, the licence of this program (`LICENSE`), and the licences
of the software packed into it (`THIRD_PARTY_NOTICES.md` and the `licenses` folder).

## Update

1. Quit the tool from its tray icon.
2. Delete the old program folder, or rename it. Do not extract a new version over an old one:
   files that the new version no longer has would stay behind.
3. Extract the new ZIP and run the new `nightreign-boss-timer.exe`.

Your settings and your records are kept outside the program folder, so updating or deleting the
program does not touch them:

| What | Where |
|---|---|
| Settings (regions, hotkeys, tables) | `%APPDATA%\nightreign-boss-timer\` |
| Records | `Documents\nightreign-boss-timer\records.csv`, unless you chose another folder |
| Log, for problem reports | `%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log` |

## Uninstall

1. Quit the tool from its tray icon.
2. Delete the program folder.
3. To remove everything, also delete `%APPDATA%\nightreign-boss-timer\` and
   `%LOCALAPPDATA%\nightreign-boss-timer\`. Delete the records folder only if you no longer
   want your fight history.

The tool installs no drivers and no services, writes nothing to the registry, and writes
nothing to the game's folder.

## Build the program yourself

1. Install [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).
2. Get the code, the text model, and build:

   ```powershell
   git clone https://github.com/sunfish-LittleKight/nightreign-boss-timer.git
   cd nightreign-boss-timer
   uv sync --dev
   uv run python tools/fetch_model.py
   uv run python tools/build_exe.py
   ```

3. The program is the folder `dist\nightreign-boss-timer`, and
   `dist\nightreign-boss-timer-<version>-windows.zip` is the same folder packed. The build
   starts the program once with `--self-test` and fails if that fails. It takes about two
   minutes.

The same build runs on GitHub: see the **Build** workflow, and "Making a release" in
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Running from source

For development, or to try a change without building. Settings, records and the log are in
the same places as for the packaged program.

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

   Or run the version with the overlay and tray icon. The first time, a short setup guide
   opens. Its tray menu switches the table, opens the records
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
| `--settings PATH` | settings file to use (overlay version only) | `%APPDATA%\nightreign-boss-timer\settings.json` |
| `--self-test` | start, check that every part loads, and exit (overlay version only) | off |

The command-line version has no overlay, no settings window and no calibration screen of its
own. It uses the regions calibrated in the overlay version, and assumes a 16:9 game image until
then.

To measure what the tool costs on your PC, run this with the game open:

```powershell
uv run python tools/bench_capture.py
```

For developers, the checks are `uv run ruff check .` and `uv run pytest`. uv downloads the right
Python version on its own. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the workflow.

## Troubleshooting installation

| Problem | What to check |
|---|---|
| Nothing seems to happen | Look for the icon in the system tray, behind the **^** arrow. |
| The program does not start | Extract the whole ZIP first. Check that antivirus did not remove files from the folder. Look at the log file. |
| Windows blocks the program | It is not signed. In the SmartScreen window choose **More info**, then **Run anyway**. |
| The tray icon shows a gold dot, or the status bar says `Game: not found` | Start the game, in windowed or borderless windowed mode. |
| The overlay is not visible | Set the game to windowed or borderless windowed, not fullscreen. |
| Hotkeys do nothing | Another program may already use that shortcut. The Hotkeys page marks shortcuts that failed to register. |

## Safety

The tool only looks at screen pixels. It does not read game memory, inject code, or change game
files. No third-party tool can be guaranteed safe with anti-cheat software, so you use it at your
own risk.
