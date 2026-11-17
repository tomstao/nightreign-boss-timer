# Contributing

Thanks for helping. The project is at the planning stage, so the most useful contributions right
now are game footage, boss name corrections, and comments on the [plan](docs/PLAN.md).

## Ground rules

- **Screen pixels only.** Changes that read game memory, inject into the game, or modify game
  files will not be accepted. This is what keeps the tool usable alongside anti-cheat.
- **No copied code or assets from AGPL or GPL projects**, including other Nightreign overlays.
  This project is MIT. Ideas are fine, files are not.
- **No game assets in the repository** beyond small screenshot crops needed for tests.
- **Performance is a feature.** A change to the capture or detection loop needs before and after
  numbers. See the performance budget in the plan.

## Setup

Install [uv](https://docs.astral.sh/uv/), then:

```powershell
uv sync --dev
uv run pre-commit install
```

## Before opening a pull request

```powershell
uv run ruff check .
uv run ruff format .
uv run pytest
```

CI runs the same commands and must pass.

## Code style

- Formatting and linting are done by Ruff with the settings in `pyproject.toml`. Do not format by hand.
- Line length is 100.
- Add type hints to new functions.
- Detection logic is tested by replaying recorded frames, not by playing the game. A change to
  detection needs a test that fails without it.
- Keep source files and config ASCII where possible. Game text in Chinese belongs in data files
  saved as UTF-8.

## Commits and pull requests

- One topic per pull request.
- Write the commit subject in the imperative: "Add bar detector", not "Added" or "Adds".
- Say what changed and why in the pull request description, and how you tested it.
- Add a line to `CHANGELOG.md` under "Unreleased" for anything a user would notice.

## Reporting detection problems

Wrong or missed detections can only be fixed with the frames that caused them. Attach a
screenshot or short clip, and state your game language, resolution, and whether HDR is on.

## Conduct

Be respectful and assume good faith. See the [code of conduct](CODE_OF_CONDUCT.md).
