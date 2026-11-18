# nightreign-boss-timer

Records how long each boss fight takes in ELDEN RING NIGHTREIGN by reading the boss health bar
from the screen. Built to cost no measurable game FPS.

> **Status: early, and used by its author.** Recording, the overlay, the tray menu, the main
> window, region calibration, global hotkeys and first-run setup all work, in English, 简体中文
> and 繁體中文. The author uses it with the game at 2560x1440 in Simplified Chinese, and
> detection is tested against 21 recorded fights at 1920x1080 and 2560x1440. Other resolutions,
> ultrawide, and the game in English or Traditional Chinese are untested, and the cost in frame
> rate has not been measured yet. No release has been published: see [Install](#install).

## What it does

- Starts a timer when a boss health bar appears and stops it when the boss's HP reaches zero.
- Saves every fight as a row in a CSV file that opens in Excel: date and time, table, boss
  name, duration, the boss HP % at the start and at the end, and your level.
- Marks a fight `complete` when the boss bar empties or the defeat text appears, and
  `incomplete` when the bar disappears while the boss still has HP.
- Treats a return to a damaged boss as a new record that starts at that boss's current HP %.
- Groups records into tables: `Arena` (Boss Arena mod training), `Normal` (regular game), or any
  name you add.
- Shows the table, boss, timer and boss HP on a small overlay that never takes a click.
- Has global hotkeys you can change, for pausing, switching tables and the other actions.
- Reads boss names in English, 简体中文 and 繁體中文, knows 210 bosses in all three, and saves
  and shows each name in the language you choose, whatever language the game is in.
- Lists your records with filters, a best time per boss, and a way to delete rows.

## Install

### Requirements

| | |
|---|---|
| Operating system | Windows 10 or Windows 11, 64-bit. Windows 10 version 2004 or later is recommended |
| Game | ELDEN RING NIGHTREIGN in **windowed** or **borderless windowed** mode |
| Game language | English, 简体中文 or 繁體中文 |
| Disk space | about 180 MB |
| Memory | about 200 MB while running |

Nothing else needs to be installed. The program brings its own Python and everything it uses.

### Download and run

1. Open this repository's **Releases** page and download the latest
   `nightreign-boss-timer-<version>-windows.zip`.

   > No release has been published yet. Until the first one, either
   > [build the program yourself](#build-it-yourself) with two commands, or open the **Actions**
   > tab, choose the latest **Build** run, and download the `nightreign-boss-timer-windows`
   > artifact, which holds the same ZIP.

2. Extract the whole ZIP to a folder you can write to, for example
   `C:\Tools\nightreign-boss-timer`. Keep all the files together, and do not run the program
   from inside the ZIP.
3. Run `nightreign-boss-timer.exe` from that folder.
4. Windows may show a SmartScreen warning, because the program is not signed. Choose
   **More info**, then **Run anyway**. Only do this for a ZIP you downloaded from this
   repository.

### First start

1. An icon appears in the system tray, near the clock. It may be behind the **^** arrow.
2. A short setup guide opens: choose the language, check that the game is found, and choose the
   table and the folder for your records. You can skip it and change everything later.
3. Set the game to windowed or borderless windowed mode and fight a boss. Recording is
   automatic.
4. If your game image is not 16:9, or fights are not recorded, calibrate the two regions: get a
   boss health bar on screen and press `Ctrl+Alt+C`.

Click the tray icon for the main window: your records, tables, hotkeys, regions and settings.
**Quit** is in the tray icon's right-click menu. The [user guide](docs/USER_GUIDE.md) explains
each part.

### Where your files are

Your records and settings are kept outside the program folder, so updating or deleting the
program does not touch them.

| What | Where |
|---|---|
| Records | `Documents\nightreign-boss-timer\records.csv`, unless you chose another folder |
| Settings | `%APPDATA%\nightreign-boss-timer\settings.json` |
| Log, for problem reports | `%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log` |

To open one of these, paste the path into the address bar of File Explorer.

### Update

1. Quit the tool from its tray icon.
2. Delete the old program folder, or rename it.
3. Extract the new ZIP and run the new `nightreign-boss-timer.exe`.

### Uninstall

1. Quit the tool from its tray icon.
2. Delete the program folder.
3. To remove everything, also delete `%APPDATA%\nightreign-boss-timer` and
   `%LOCALAPPDATA%\nightreign-boss-timer`. Delete `Documents\nightreign-boss-timer` only if you
   no longer want your fight history.

The tool installs no drivers and no services, writes nothing to the registry, and writes nothing
to the game's folder.

### If something goes wrong

| Problem | What to try |
|---|---|
| Nothing seems to happen when I run it | Look for the icon in the system tray, behind the **^** arrow. The program has no window until you click that icon. |
| The program does not start at all | Extract the whole ZIP first. Check that antivirus did not remove files from the folder. Look at the log file. |
| The tray icon shows a gold dot | The game window was not found. Start the game, in windowed or borderless windowed mode. |
| Fights are not recorded | Open the main window's **Regions** page with a boss bar on screen. It shows what the tool sees. Calibrate with `Ctrl+Alt+C`. |
| A hotkey does nothing | Open the **Hotkeys** page. A shortcut marked `(not working)` is used by another program: choose another. |
| The overlay is not visible | Set the game to windowed or borderless windowed. Check **Show overlay** in the tray menu. |

More in the [user guide](docs/USER_GUIDE.md#troubleshooting). When reporting a problem, attach
the log file and say which game language, resolution and window mode you use.

## Build it yourself

You need [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/). uv downloads the
right Python by itself.

```powershell
git clone https://github.com/tomstao/nightreign-boss-timer.git
cd nightreign-boss-timer
uv sync --dev
uv run python tools/fetch_model.py
uv run python tools/build_exe.py
```

- `fetch_model.py` downloads the text recognition model used for boss names (21 MB, once) and
  checks it against a known checksum.
- `build_exe.py` builds the folder `dist\nightreign-boss-timer` with
  `nightreign-boss-timer.exe` in it, starts the result once to test it, and packs
  `dist\nightreign-boss-timer-<version>-windows.zip`. It takes about two minutes.

Copy the folder anywhere and run the `.exe`, as described under [Install](#install).

## Run from source

For development, or to try a change without building:

```powershell
uv sync --dev
uv run python tools/fetch_model.py
uv run python -m nightreign_boss_timer.ui.app
```

| Option | Meaning |
|---|---|
| `--title TEXT` | title of the game window, if it is not `ELDEN RING NIGHTREIGN` |
| `--records PATH` | write the records CSV somewhere else |
| `--settings PATH` | use another settings file |
| `--self-test` | start, check that every part loads, and exit |

The packaged program takes the same options. There is also a command-line version without any
window, `uv run python -m nightreign_boss_timer --table Arena`, which prints each fight and is
stopped with Ctrl+C.

To measure what the tool costs on your PC, run `uv run python tools/bench_capture.py` with the
game open.

## How it works

The tool is a separate program that only looks at screen pixels.

1. It copies two small regions of the game window: the boss health bar and the defeat text.
2. A colour and shape check on the bar runs ten times per second during a fight and gives the
   boss HP %. No model is involved, which is what keeps it cheap.
3. Text recognition runs only a few times per fight, on the CPU, to read the boss name when the
   bar appears.
4. The defeat text is recognised by its look. It is never read as text, so it needs no language
   handling.

## Safety

The tool does not read game memory, inject code, or change game files. This is the same approach
other screen-reading Nightreign tools use. No third-party tool can be guaranteed safe with
anti-cheat software, so you use it at your own risk.

This project is not affiliated with FromSoftware or Bandai Namco.

## Use of AI

Most of the code, tests and documentation in this repository were written with an AI coding
assistant (Claude Code, by Anthropic), directed and reviewed by the maintainer. Commits made
that way carry a `Co-Authored-By: Claude` line.

What that means for you:

- The maintainer decides what is built and merges every change, and every change has to pass
  the tests. Detection is checked against recorded fights, as described in
  [docs/observations.md](docs/observations.md).
- AI-written code can be wrong in ways that look right. Where something has not been tested,
  the documentation says so. Treat the tool as early software, and please report what
  misbehaves.
- No AI runs in the program itself, and nothing is sent anywhere. Boss names are read by a
  small text recognition model that runs on your own PC.
- The Chinese texts of the interface were written with AI and have not been reviewed by a
  native speaker yet.

As the [licence](LICENSE) says, the software comes with no warranty.

## Development

```powershell
uv sync --dev
uv run pre-commit install
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI runs the same checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules, the
workflow and how a release is made.

## Documentation

- [User guide](docs/USER_GUIDE.md): setup, everyday use, records, tables, hotkeys, troubleshooting
- [Installation](docs/INSTALL.md): the same steps as above in more detail
- [Plan](docs/PLAN.md): goal, recording rules, design, milestones, open decisions
- [UI design](docs/UI.md): tray, overlay, main window, calibration, first-run setup
- [Observations](docs/observations.md): measurements of the boss bar from real footage
- [API reference](docs/API.md): what each module does and its public functions
- [Research](docs/research.md): terminology, best practice, notes on existing tools
- [Contributing](CONTRIBUTING.md), [Changelog](CHANGELOG.md), [Security policy](SECURITY.md)

## Licence

[MIT](LICENSE). The packaged program also contains other open-source software and a text
recognition model, each under its own licence: see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
