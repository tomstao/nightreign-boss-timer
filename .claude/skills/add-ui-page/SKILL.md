---
name: add-ui-page
description: Add a page to the nightreign-boss-timer main window, or a new user action that the tray menu, a page and a hotkey can all trigger. Use when adding a page, a setting on a page, a tray menu entry, or a hotkey action, and when deciding where UI logic should live.
---

# Add a page or an action

The UI has one rule that keeps it testable: **decisions live in the controller, widgets only draw
and forward input.**

```
tray menu ──┐
main window ├──> Controller ──> Settings (saved to disk), RecordStore
hotkeys ────┘        │
                     └── signals ──> everything redraws itself from the settings
```

- `ui/controller.py` holds every user action as a method: it changes the settings, saves them,
  and emits `changed`. It never draws.
- A widget calls a controller method and waits to be told to redraw. It does not change the
  settings itself, and it does not update its own labels after a click.
- `ui/app.py` only wires things together. If you are adding logic there, it belongs elsewhere.

## Add an action

1. Add a method to `Controller`. Change the settings, call `self.save()`, emit `self.changed`.
   If the overlay should confirm it, emit `self.notice` with translated text.
2. If the action can fail for a reason the user should read, return the reason as translated
   text and an empty string on success, as `add_table` and `set_hotkey` do.
3. Anything outside the process (opening a file, the clock, Windows) is passed into the
   controller's constructor or set as an attribute by the app, so tests can replace it. See
   `opener`, `clock`, `probe` and `hotkey_applier`.
4. To make it a hotkey: add its name to `DEFAULT_HOTKEYS` in `settings.py` (an empty string
   means not set by default), add it to the handlers in `Controller.run_action`, and add a
   `hotkey.<name>` text in all three languages. A test fails if the label is missing.
5. To put it in the tray menu, add an entry in `Tray.rebuild` and update the expected list in
   `tests/test_tray.py`.

## Add a page

1. Create `ui/<name>_page.py` with a class that inherits `Page` from `ui/pages.py`:

   ```python
   class ThingsPage(Page):
       key = "things"  # the sidebar shows the translation of "page.things"

       def __init__(self, controller: Controller) -> None:
           super().__init__(controller)
           ...  # build widgets, connect them to controller methods

       def refresh(self) -> None: ...  # set every text and value from controller.settings
   ```

2. `refresh()` is called when the page is shown and after every controller change. It must set
   **every** text, because the language can change while the window is open. Do not set text in
   `__init__`.
3. While `refresh()` puts values into input widgets, block their signals, or showing a value
   counts as the user changing it. See `SettingsPage.refresh`.
4. Add the page to `default_pages` in `ui/main_window.py`, and a `page.<key>` text in all three
   languages (see the `add-ui-text` skill).
5. A page that reads the screen or a file on a timer does so only while visible: start the timer
   in `showEvent`, stop it in `hideEvent`. See `RegionsPage`.
6. A dialog that would block (a file chooser, a message box) is passed in as a function with a
   default, so tests can answer it. See `choose_folder` in `SettingsPage`.

## Test it

Use `Recorder` from `tests/ui_support.py`: a real controller whose settings file, records file
and "open with Windows" all point into a temporary folder.

```python
recorder = Recorder(tmp_path)
window = MainWindow(recorder.controller, [ThingsPage(recorder.controller)])
page = window.pages[0]
```

Putting the page in a real `MainWindow` matters: the window is what redraws the page after a
change, and a test without it passes while the real page shows stale text.

Cover at least: what the page shows at first, each button, a refused input with its message,
that a change reaches the saved settings file (`settings_file.load(recorder.settings_path)`),
and the page in `zh_CN` or `zh_TW`. Then follow the `check-ui` skill to look at it.

## Finish

- Add the module and its public names to `docs/API.md`. A test fails until you do.
- Describe what the user sees in `docs/USER_GUIDE.md`, and add a line to `CHANGELOG.md`.
- If the page shows something `docs/UI.md` designed differently, say so in the pull request.
