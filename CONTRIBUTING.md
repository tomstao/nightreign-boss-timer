# Contributing

Thanks for helping. The most useful contributions right now are game footage, boss name
corrections, test runs against the real game, and comments on the [plan](docs/PLAN.md).

The [API reference](docs/API.md) says what each module does. If you develop with Claude Code,
`CLAUDE.md` and the skills under `.claude/skills/` describe the same workflow as this file in
more detail: shipping a change, adding UI text, adding a page or an action, checking the UI, and
working with footage.

## Ground rules

- **Screen pixels only.** Changes that read game memory, inject into the game, or modify game
  files will not be accepted. This is what keeps the tool usable alongside anti-cheat.
- **No copied code or assets from AGPL or GPL projects**, including other Nightreign overlays.
  This project is MIT. Ideas are fine, files are not.
- **No game assets in the repository** beyond small screenshot crops needed for tests.
- **Performance is a feature.** A change to the capture or detection loop needs before and after
  numbers. See the performance budget in the plan.

## Using AI tools

You may use AI tools to write a contribution. Most of this project was written that way. The
same rules apply as for any other change:

- You are responsible for what you submit. Read it, run it, and be able to explain it.
- Say in the pull request that AI was used, and what you tested yourself.
- Do not submit code an AI reproduced from a project whose licence does not allow it here. The
  rule about AGPL and GPL code above applies whoever typed it.

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
- Update `docs/API.md` when you add or change a module or a public function. A test checks it.

## How changes reach `main`

`main` is protected. Nobody pushes to it directly, maintainers included.

- Every change is a pull request, merged by squashing, so `main` has one commit per change.
- The three CI checks must pass first: **Lint and format**, **Test (Python 3.11)** and
  **Test (Python 3.13)**. The branch must be up to date with `main`.
- Open discussions on the pull request must be resolved.
- `main` cannot be force-pushed or deleted.

A pull request from a fork runs CI without access to anything secret. The first one from a new
contributor waits for a maintainer to allow the run.

These rules, and the security settings (secret scanning with push protection, private
vulnerability reports, Dependabot alerts), are set by `tools/protect_main.sh`. A maintainer
runs it again after changing it.

Workflow actions are pinned to an exact commit, with the version in a comment. Dependabot
proposes the updates.

## The README in other languages

`README.zh-CN.md` and `README.zh-TW.md` are shorter translations of `README.md`, which is the
reference. A change to what the English page tells users should be made in all three. If you
cannot write one of the languages, say so in the pull request and someone else will.

## Making a release

For maintainers. A release is a ZIP of the packaged program, built by CI.

1. Set the version in `pyproject.toml`, run `uv lock`, and in `CHANGELOG.md` rename "Unreleased"
   to the version and date. Merge that as a normal pull request.
2. Tag the merge commit with the same version and push the tag:

   ```powershell
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. The **Build** workflow builds the program, runs its self-test, and attaches
   `nightreign-boss-timer-<version>-windows.zip` to a draft release. It fails if the tag and
   the version in `pyproject.toml` differ.
4. Download the ZIP from the draft, extract it on a PC and run it against the game. Then
   publish the draft.

To build locally instead: `uv run python tools/fetch_model.py`, then
`uv run python tools/build_exe.py`. The result is in `dist/`.

## Reporting detection problems

Wrong or missed detections can only be fixed with the frames that caused them. Attach a
screenshot or short clip, and state your game language, resolution, and whether HDR is on.

## Conduct

Be respectful and assume good faith. See the [code of conduct](CODE_OF_CONDUCT.md).
