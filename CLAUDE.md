# nightreign-boss-timer

A Windows tool that reads the boss health bar from the screen in ELDEN RING NIGHTREIGN and records
how long each fight takes. Python, uv, NumPy, ONNX Runtime, PySide6.

## Read first

- `docs/PLAN.md`: the plan. Its "Recording rules" section holds the project owner's decisions and
  overrides everything else.
- `docs/UI.md`: the UI design. `docs/observations.md`: what was measured from game footage.
- `docs/API.md`: what each module does and its public functions.
- `CONTRIBUTING.md`: ground rules and code style.

## Hard limits

- Screen pixels only. No game memory access, no injection, no changes to game files.
- No code or assets copied from AGPL or GPL projects, including other Nightreign overlays.
- Game footage and full screenshots are never committed. Only the small crops under
  `tests/fixtures/` are.
- The capture and detection loop must stay cheap: see the performance budget in the plan.

## Commands

```powershell
uv sync --dev
uv run python tools/fetch_model.py          # once: the text model for boss names
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python -m nightreign_boss_timer.ui.app    # overlay and tray icon
uv run python -m nightreign_boss_timer           # command-line version
```

## Conventions

- Small pull requests, one topic each. Follow the `ship-change` skill.
- No user-facing text in code. It goes through `src/nightreign_boss_timer/i18n/` in English,
  简体中文 and 繁體中文. Follow the `add-ui-text` skill.
- A change a user can see updates `docs/USER_GUIDE.md`, `docs/INSTALL.md` and `CHANGELOG.md` in
  the same pull request. A new or changed public function updates `docs/API.md`.
- Detection is tested by replaying recorded pixels, not by playing the game. Follow the
  `detector-footage` skill.
- UI is tested in memory and then looked at. Follow the `check-ui` skill.
- Logic lives outside Qt where it can: `calibration.py`, `ui/presenter.py` and `ui/controller.py`
  hold decisions, and widgets only draw and forward input.
- Plain words in comments and docs. Line length 100. Source files stay ASCII where possible.

## Skills

Project skills are in `.claude/skills/`:

| Skill | Use it when |
|---|---|
| `ship-change` | turning finished work into a pull request, or merging a stack of them |
| `add-ui-text` | adding or changing any text the user sees |
| `check-ui` | building or changing a window, the overlay or the tray menu |
| `detector-footage` | changing detection, or adding test pixels from new footage |
