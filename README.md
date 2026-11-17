# nightreign-boss-timer

Records how long each boss fight takes in ELDEN RING NIGHTREIGN by reading the boss health bar
from the screen. Built to cost no measurable game FPS.

> **Status: early development.** A command-line version records fights with default regions.
> The overlay, the settings window and region calibration are not built yet.
> See the [plan](docs/PLAN.md) for milestones.

## What it will do

- Start a timer when a boss health bar appears and stop it when the bar goes away.
- Save every fight as a row in a CSV file that opens in Excel: date and time, table, boss
  name, duration, and the boss HP % at the start and at the end.
- Group records into tables: `Arena` (Boss Arena mod training), `Normal` (regular game), or any
  name you add.
- Let you set your own hotkeys for switching tables, pausing tracking, and the other actions.
- Mark a fight `complete` when the defeat text appears, and `incomplete` when the bar disappears
  without it.
- Treat a return to a damaged boss as a new record that starts at that boss's current HP %.
- Read boss names in English, 简体中文 and 繁體中文.

## How it works

The tool is a separate program that only looks at screen pixels.

1. It captures two small regions of the game window: the boss health bar and the defeat text.
2. A colour check on the bar runs a few times per second and gives the boss HP %.
3. Text recognition runs only a few times per fight, to read the boss name when the bar appears
   and the defeat text when it goes away.

On first use you mark the health bar and the defeat text regions by hand. Automatic detection of
those regions is planned for later.

## Requirements

- Windows 10 or 11
- The game in windowed or borderless windowed mode (exclusive fullscreen is not supported)

## Safety

The tool does not read game memory, inject code, or change game files. This is the same approach
other screen-reading Nightreign tools use. No third-party tool can be guaranteed safe with
anti-cheat software, so you use it at your own risk.

This project is not affiliated with FromSoftware or Bandai Namco.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --dev
uv run pre-commit install
```

Checks, the same ones CI runs:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Try the command-line version

An early version without overlay or settings window. It uses default regions for a 16:9 game
image.

```powershell
uv run python tools/fetch_model.py
uv run python -m nightreign_boss_timer --table Arena
```

The first command downloads the text recognition model (21 MB, once). Without it the tool still
times fights but records the boss as `unknown`.

Start the game in windowed or borderless windowed mode, then fight a boss. Each finished fight is
printed and appended to `Documents\nightreign-boss-timer\records.csv`. Stop with Ctrl+C.

To measure what it costs on your PC, run `uv run python tools/bench_capture.py` with the game open.

## Documentation

- [Installation](docs/INSTALL.md): requirements, install, update, uninstall, running from source
- [User guide](docs/USER_GUIDE.md): setup, everyday use, records, tables, hotkeys, troubleshooting
- [Plan](docs/PLAN.md): goal, recording rules, design, milestones, open decisions
- [UI design](docs/UI.md): tray, overlay, main window, calibration, first-run setup
- [Observations](docs/observations.md): measurements of the boss bar from real screenshots
- [Research](docs/research.md): terminology, best practice, notes on existing tools
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Security policy](SECURITY.md)

## Licence

[MIT](LICENSE)
