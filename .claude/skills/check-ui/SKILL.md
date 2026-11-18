---
name: check-ui
description: Test and look at a nightreign-boss-timer window, overlay or tray menu without the game running. Use when building or changing anything under src/nightreign_boss_timer/ui/, when a UI change needs to be verified, or when a stand-in for the game window is needed.
---

# Check the UI

The game is not needed for most UI work. There are three levels, and a UI change should pass all
that apply.

## 1. Tests in memory

UI tests draw into memory with Qt's `offscreen` platform, so they need no desktop and show
nothing. Copy the top of `tests/test_calibration_window.py`:

```python
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtTest import QTest

    ...


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])
```

- Imports of PySide6 and of `ui` modules go under `if sys.platform == "win32":`, because lint
  runs on Linux and collection must not fail there.
- Drive widgets with `QTest.mouseClick`, `QTest.keyClick` and by calling their methods. Assert on
  what the user would see: `label.text()`, `button.isEnabled()`, `widget.isVisible()`.
- Anything outside the process is passed in so tests can replace it: the screenshot source of the
  calibration window, the `opener` and `settings_path` of `Controller`. Never let a test write
  the real settings file or open a real program.
- A connection made with `Qt.ConnectionType.QueuedConnection` runs on the next
  `application.processEvents()`.
- Test each window once in `zh_CN` or `zh_TW` too.
- Give tests real pixels where it matters: paste a region from `tests/fixtures/*.npz` into a
  plain full-size picture, as `game_picture()` in `tests/test_calibration_window.py` does.

## 2. Look at it

Passing tests do not show a broken layout. Render the window to a PNG and look at the file:

```python
application = QApplication([])
window = TheWindow(...)
window.resize(1280, 800)
window.show()
application.processEvents()
window.grab().save("window.png")
```

Run this on the normal platform, not `offscreen`: the offscreen platform has no fonts and draws
every letter as a box. Save the PNG outside the repository.

## 3. Real screen, with a stand-in for the game

`standin_game.py` in this folder shows a screenshot in a borderless window with a title of your
choice, at an exact pixel size. The tool then finds and captures it like the game:

```powershell
uv run python .claude/skills/check-ui/standin_game.py path\to\screenshot.png --size 1920x1080
uv run python -m nightreign_boss_timer.ui.app --title "NBT stand-in"
```

Use a full-frame game screenshot with a boss bar on it. To check a whole fight, play a recorded
clip in a media player window and pass that window's exact title to `--title`.

What this covers: finding the window, real screen capture, the calibration screenshot, the
overlay over a "game". What it does not cover: the real game's window title, borderless mode,
and the frame rate cost. Say so in the pull request.

## Things that have gone wrong before

- Tests passed and the run still failed with a crash on exit. Windows that outlive the Qt
  application crash Python as it shuts down. `tests/conftest.py` destroys every window at the
  end of the run, so check the exit code of `uv run pytest`, not only its last line.
- A Qt window cannot be shown larger than about two thirds of the screen unless its size is
  fixed. The stand-in uses `setFixedSize` for that reason.
- Clearing a menu from inside one of its own entries crashes. `Tray.rebuild` is connected with a
  queued connection.
- The calibration window covers the game, so it hides itself before taking a screenshot.
- The overlay is visible to screen capture on some PCs. Keep it away from the watched regions.
