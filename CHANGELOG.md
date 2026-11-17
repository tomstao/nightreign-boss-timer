# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## Unreleased

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
