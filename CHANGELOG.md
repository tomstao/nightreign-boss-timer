# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## Unreleased

### Fixed

- A kill is now saved as `complete` when the boss bar empties and then goes away, even if no gold defeat text follows. Night bosses show a silver banner, and some bosses show none.
- One wrong HP reading no longer sticks: a record no longer starts at 0% because the bar was fading in.
- The boss bar is no longer read as empty while a skill popup covers the red part of it at low HP.
- The overlay is now left out of screen captures, so the tool cannot read its own overlay as part of the game. It no longer appears in screenshots or recordings either.

### Added

- Project plan, research notes, and recording rules.
- Project tooling: Ruff linting and formatting, pytest, pre-commit hooks, GitHub Actions CI.
- CSV record store that opens in Excel and holds rows while the file is locked.
- Boss bar detector: finds the bar in a strip of pixels and reads how full it is.
- Defeat text check: recognises the gold defeat text by its shape, without reading it.
- Fight tracker: turns detector readings into complete or incomplete fights, following the recording rules.
- Screen capture for Windows that copies only the watched regions, and a benchmark script.
- Command-line version: watches the game, prints each fight and appends it to the records file.
- Installation manual and user guide, written ahead of the first release.
- Fight tracker no longer mistakes hit flashes for the defeat text.
- Boss name reader: reads the name above the bar with a small text recognition model on the CPU.
- Records now carry the boss name, read at the start of each fight.
- Boss bar detector holds through most hit flashes.
- Settings file with tables, regions, hotkeys and timing options.
- Translation files for English, Simplified Chinese and Traditional Chinese.
- The command-line version now reads the settings file (tables, regions, timing options).
- Overlay showing table, boss, timer and boss HP, with a tray icon to pause, hide and quit.
- Region calibration window, opened from the tray menu: mark the health bar and the defeat text on a screenshot of the game, with the detector's reading shown as the box moves.
- Tray menu: switch the active table, open the records file, and an icon that shows tracking, fight, paused or needs attention.
- Main window with a status bar and an About page, opened by clicking the tray icon.
- Records page: all fights with filters, search, sorting and a per-boss summary.
- Tables page: add, rename and delete tables and choose the active one.
- Settings page: UI language (switches at once), records folder, wait time, walk-past skipping and detection rate.
- Regions page: calibration status for each region and a live preview of what the tool reads there.
- Global hotkeys: pause or resume, next table, switch to a table, show or hide the overlay, open calibration.
- Two more hotkey actions, not set by default: end the current fight now, and discard the last record (press again to undo).
- Hotkeys page: change any shortcut by pressing the keys, with conflict checks and a mark on shortcuts Windows refuses.
- The overlay can be dragged to a new place while the main window is open. The place is remembered.
- First-run setup guide: language, game check and calibration, table, records folder and hotkeys. Shown once, and again on request from the Settings page.
- A packaged Windows program: `tools/build_exe.py` builds a folder with `nightreign-boss-timer.exe`, its own Python and the text model, and a ZIP of it.
- A log file at `%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log`.
- Setting to show the overlay in screenshots and recordings, for making videos of the tool. Off by default.
