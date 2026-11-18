# API reference

What each module of `nightreign_boss_timer` is for, and the names other code is meant to use.
Names starting with an underscore are private and not listed. Each module's own docstring says
more about how it works.

This file is checked by `tests/test_api_docs.py`: every module must have a section here, and
every name in the first column of a table must exist in the code. Update it in the same pull
request as the code.

## How the pieces fit

```
capture.py (screen) --> detector.py, defeat_text.py --> tracker.py --> records.py (CSV)
     ^                        ^                             |
 regions.py              ocr.py + names.py              engine.py  <-- settings.py
 (where to look)         (boss name)               (one step at a time)
                                                            |
                              ui/app.py drives the engine with a timer and shows the result:
                              ui/presenter.py -> ui/overlay.py,  ui/tray.py,  ui/controller.py
```

- The **engine** owns the watch loop logic but has no loop of its own. Whoever drives it calls
  `Engine.step()` and waits for the delay it returns.
- **Detectors** are pure functions on arrays. They never touch the screen or the disk.
- **UI decisions** live in plain modules (`calibration.py`, `ui/presenter.py`,
  `ui/controller.py`). Widgets draw and forward input.

Arrays of pixels are always RGB, `uint8`, shape `(rows, columns, 3)`.

## Detection

### `nightreign_boss_timer.detector`

Finds the boss health bar in a strip of pixels and reads how full it is.

| Name | What it is |
|---|---|
| `measure_bar(region)` | Reads a region made with `grow_box`. Returns a `BarReading`. |
| `BarReading` | `present`, `hp` (where the visible red ends, 0.0 to 1.0), `hp_high` (the furthest the fill could reach if something covers its end), `score`. |
| `ABSENT` | The reading for "no bar". |
| `grow_box(top, bottom)` | Rows to capture for a bar whose fill spans `top` to `bottom` inclusive: the bar plus `MARGIN_HEIGHTS` bar-heights above and below. |
| `MARGIN_HEIGHTS` | How many bar-heights of scene the detector needs on each side. |

### `nightreign_boss_timer.defeat_text`

Tells whether the gold defeat text is on screen, by its look. It never reads the text.

| Name | What it is |
|---|---|
| `measure_defeat_text(region)` | Reads the defeat text box. Returns a `DefeatReading`. |
| `DefeatReading` | `visible`, plus what decided it: `gold` share, `span`, `strokes`, `band_brightness`. |

### `nightreign_boss_timer.tracker`

The recording rules as a state machine. Fed one sample at a time, it says when a fight ended.

| Name | What it is |
|---|---|
| `FightTracker(wait_window_s, skip_walk_pasts)` | The state machine for one stream of readings. |
| `FightTracker.update(now, bar, defeat_text)` | Feed one sample. Returns a `FightOutcome` on the sample that ends a fight, else `None`. |
| `FightTracker.in_fight` | True from the confirmed start until the outcome. |
| `FightTracker.started_at` | The tracker-clock time the current fight began. |
| `FightTracker.hp` | The current smoothed HP, or `None`. |
| `FightTracker.watching_for_defeat` | True while the defeat text region needs to be read. |
| `FightOutcome` | `status`, `started_at`, `duration_s`, `start_hp_pct`, `end_hp_pct`. |
| `FULL_HP` | A reading at or above this is written as 100%. |

### `nightreign_boss_timer.ocr`

Reads one line of text, the boss name, with a small ONNX model on the CPU.

| Name | What it is |
|---|---|
| `NameReader(model_path)` | Loads the model. Raises `FileNotFoundError` if it was not downloaded. |
| `NameReader.read(region)` | Returns a `TextReading`. |
| `TextReading` | `text` and `confidence`. |
| `default_model_path()` | Where the model file is kept. `NBT_MODEL_DIR` overrides the folder. |
| `MODEL_URL` | Where `tools/fetch_model.py` downloads it from. |
| `MODEL_SHA256` | The checksum the download must match. |

### `nightreign_boss_timer.names`

Settles on a boss name from several readings.

| Name | What it is |
|---|---|
| `NameVote` | Collects readings for one fight. |
| `NameVote.add(text, confidence)` | Add one reading. Uncertain ones are ignored. |
| `NameVote.settled` | True when no more readings are needed. |
| `NameVote.name` | The winning name, or `UNKNOWN`. |
| `UNKNOWN` | The boss name stored when it could not be read. |
| `language_of(name)` | `en`, `zh`, or empty for `UNKNOWN`. |

## Screen

### `nightreign_boss_timer.regions`

Where the watched regions are inside the game image.

| Name | What it is |
|---|---|
| `Box` | A rectangle in pixels: `left`, `top`, `width`, `height`. |
| `Fractions` | A rectangle as fractions of the game image: `left`, `right`, `top`, `bottom`. This is what the settings file stores. |
| `DEFAULT_BAR` | The bar's measured position on a 16:9 image. |
| `DEFAULT_DEFEAT_TEXT` | The defeat text's measured position on a 16:9 image. |
| `bar_region(window, bar)` | Screen pixels to grab for the bar detector. |
| `name_region(window, bar)` | Screen pixels holding the boss name, worked out from the bar. |
| `defeat_text_region(window, text)` | Screen pixels to grab for the defeat text check. |

### `nightreign_boss_timer.capture`

Copies small regions of the screen into arrays with GDI. Windows only.

| Name | What it is |
|---|---|
| `enable_dpi_awareness()` | Call once at start, so coordinates mean real pixels. |
| `find_window(title)` | The drawable area of the window with exactly this title, as a `Region`, or `None`. |
| `Region` | A rectangle in screen pixels. Same fields as `regions.Box`. |
| `ScreenGrabber(width, height)` | Grabs one fixed-size region, reusing its Windows resources. A context manager. |
| `ScreenGrabber.grab(left, top)` | Copy the region at these screen pixels. |
| `WindowsScreen` | The real screen in the shape the engine expects: `find_window`, `grab(box)`, `close`. |
| `CaptureError` | Windows refused to copy the region. |

### `nightreign_boss_timer.calibration`

Region calibration without any drawing: the box the user drags, and what the detectors see in it.

| Name | What it is |
|---|---|
| `Selection` | A box in picture pixels. `right` and `bottom` are one past the last pixel inside. |
| `RegionKind` | `BAR` or `DEFEAT_TEXT`. |
| `Corner` | The four corners of a selection. |
| `fit(selection, width, height)` | The nearest allowed box: ordered, not too small, inside the picture. |
| `move(selection, dx, dy, width, height)` | Shift the box, stopping at the edges. |
| `drag_corner(selection, corner, x, y, width, height)` | Put one corner somewhere else. |
| `to_fractions(selection, kind, width, height)` | The box as stored in settings. |
| `from_fractions(fractions, kind, width, height)` | The reverse. |
| `starting_selection(saved, kind, width, height)` | The saved box, or the 16:9 default. |
| `read_bar(picture, fractions)` | What the bar detector reads in a picture of the whole game image. |
| `read_defeat_text(picture, fractions)` | The same for the defeat text. |

## Data

### `nightreign_boss_timer.records`

Fight records and the CSV file they are stored in.

| Name | What it is |
|---|---|
| `FightRecord` | One fight: `started_at`, `table`, `boss`, `language`, `status`, `duration_s`, `start_hp_pct`, `end_hp_pct`. |
| `Status` | `COMPLETE` or `INCOMPLETE`. |
| `RecordStore(path)` | The CSV file. |
| `RecordStore.append(record)` | Save a record. Returns `False` if it had to be held because the file is locked. |
| `RecordStore.read_all()` | All saved records, oldest first. |
| `RecordStore.flush_pending()` | Try to write held rows. |
| `RecordStore.pending_count()` | How many rows are held. |
| `RecordStore.ensure_file()` | Create the file with its header row if it is missing. |
| `format_duration(seconds)` | `mm:ss.s`. |
| `COLUMNS` | The CSV columns, in order. |

### `nightreign_boss_timer.settings`

The user's settings, kept in one JSON file. Loading never fails.

| Name | What it is |
|---|---|
| `Settings` | All settings: language, tables, active table, records folder, timing, regions, hotkeys. |
| `Settings.add_table(name)` | Add a table. Raises `TableError` for an empty or duplicate name. |
| `Settings.rename_table(old, new)` | Rename a table. |
| `Settings.delete_table(name)` | Delete a table. Built-in tables cannot be deleted. |
| `Settings.set_active_table(name)` | Choose the table new fights are saved under. |
| `Settings.next_table()` | Make the next table active, wrapping around. |
| `Settings.table_names()` | Names in display order. |
| `Table` | `name`, `builtin`, `hotkey`. |
| `TableError` | A table change that is not allowed. |
| `load(path)` | Read the file. Missing or damaged files give defaults. |
| `save(settings, path)` | Write the file safely. |
| `default_settings_path()` | `%APPDATA%\nightreign-boss-timer\settings.json`. |
| `DEFAULT_HOTKEYS` | Action name to default shortcut. |
| `UI_LANGUAGES` | The supported UI languages. |

### `nightreign_boss_timer.i18n`

Text shown to the user, in every supported language.

| Name | What it is |
|---|---|
| `Translator(language)` | Call it with a key and placeholder values to get text. Set `.language` to switch. |
| `load_catalogue(language)` | All texts of one language. |
| `LANGUAGES` | `en`, `zh_CN`, `zh_TW`. |
| `FALLBACK` | The language used when a key is missing: `en`. |

## Running

### `nightreign_boss_timer.engine`

Joins capture, detectors, tracker, name reading and the record store, one step at a time.

| Name | What it is |
|---|---|
| `Engine(settings, screen, store, reader)` | The watch loop logic. `title`, `clock` and `wall_clock` can be replaced for tests. |
| `Engine.step()` | Look at the screen once. Returns a `StepResult`. |
| `Engine.paused` | Set to `True` to stop looking. |
| `StepResult` | `snapshot`, `record` (set when a fight just ended), `saved`, `delay_s` (how long to wait before the next step). |
| `Snapshot` | What to show now: `state`, `table`, `boss`, `hp`, `elapsed_s`. |
| `State` | `PAUSED`, `NO_GAME`, `IDLE`, `FIGHT`. |
| `Screen` | The interface the engine needs from the screen: `find_window(title)` and `grab(box)`. |
| `NameSource` | The interface for reading a name: `read(region)`. |
| `records_path(settings)` | Where `records.csv` is for these settings. |
| `to_record(outcome, table, now, wall_now, boss)` | Turn a tracker outcome into a `FightRecord`. |
| `GAME_TITLE` | The game window title looked for by default. |

### `nightreign_boss_timer.__main__`

The command-line version: `python -m nightreign_boss_timer`.

| Name | What it is |
|---|---|
| `main()` | Parses `--table`, `--records`, `--title` and runs until Ctrl+C. |
| `describe(record)` | One printed line for a finished fight. |

## User interface

All of `nightreign_boss_timer.ui` needs PySide6 and Windows.

### `nightreign_boss_timer.ui.app`

Starts everything: `python -m nightreign_boss_timer.ui.app`.

| Name | What it is |
|---|---|
| `App` | Builds the engine, controller, overlay, tray and calibration window, and drives the engine with a timer. |
| `main()` | Parses `--title` and `--records` and runs the Qt event loop. |

### `nightreign_boss_timer.ui.controller`

Every action the user can take, shared by the tray, the windows and the hotkeys.

| Name | What it is |
|---|---|
| `Controller(settings, translate, store)` | Holds the settings and the on/off state. `settings_path` and `opener` can be replaced for tests. |
| `Controller.changed` | Signal: something shown in a menu or window is now different. |
| `Controller.notice` | Signal with a short message for the overlay. |
| `Controller.calibration_requested` | Signal: open the calibration window. |
| `Controller.set_tracking(on)` | Pause or resume. Also `toggle_tracking()`. |
| `Controller.set_overlay_visible(on)` | Show or hide the overlay. Also `toggle_overlay()`. |
| `Controller.set_table(name)` | Switch the active table and save. Also `next_table()`. |
| `Controller.open_records_file()` | Open `records.csv` in the program Windows uses for it. |
| `Controller.open_records_folder()` | Open the folder that holds it. |
| `Controller.calibrate()` | Ask for the calibration window. |
| `Controller.save()` | Write the settings file. |

### `nightreign_boss_timer.ui.presenter`

Decides what the overlay says. No drawing.

| Name | What it is |
|---|---|
| `overlay_text(snapshot, translate)` | The lines to show. Optional `result`, `result_age_s`, `best_s`, `notice`, `notice_age_s`. |
| `OverlayText` | `lines` (none hides the overlay) and `warning`. |
| `best_time(records, boss, table)` | Fastest complete fight from full health, or `None`. |
| `RESULT_SECONDS` | How long a result stays on the overlay. |
| `NOTICE_SECONDS` | How long a notice stays. |

### `nightreign_boss_timer.ui.overlay`

The see-through panel over the game. It never takes focus or clicks.

| Name | What it is |
|---|---|
| `Overlay` | The window. |
| `Overlay.show_text(text)` | Replace what it says with an `OverlayText`. |
| `Overlay.set_enabled(enabled)` | Turn it on or off. |

### `nightreign_boss_timer.ui.tray`

The tray icon and its menu.

| Name | What it is |
|---|---|
| `Tray(controller, quit_app)` | Builds the icon and menu, and rebuilds the menu when the controller changes. |
| `Tray.set_state(state)` | Change the icon. |
| `Tray.rebuild()` | Rebuild the menu from the settings. |
| `IconState` | `TRACKING`, `FIGHT`, `PAUSED`, `ATTENTION`. |
| `make_icon(state)` | The icon picture for a state. |

### `nightreign_boss_timer.ui.region_canvas`

A picture of the game with one box on it that the user drags.

| Name | What it is |
|---|---|
| `RegionCanvas` | The widget. |
| `RegionCanvas.set_picture(picture, selection)` | Show a picture with a starting box. |
| `RegionCanvas.selection` | The current box, in picture pixels. |
| `RegionCanvas.set_selection(selection)` | Change the box from code. |
| `RegionCanvas.selection_changed` | Signal: the box changed. |
| `RegionCanvas.to_widget(x, y)` | Where a picture position is drawn. |
| `RegionCanvas.to_picture(position)` | The picture position under a widget position. |
| `to_image(picture)` | A Qt image from an RGB array. |

### `nightreign_boss_timer.ui.calibration_window`

The two-step calibration window.

| Name | What it is |
|---|---|
| `CalibrationWindow(settings, translate, take_picture, on_saved)` | `take_picture` returns the game image or `None`. `on_saved` runs after each region is written into the settings. |
| `CalibrationWindow.start()` | Take a screenshot and open at the first step. |
| `CalibrationWindow.retake()` | Hide, take a new screenshot, come back. |
| `CalibrationWindow.load_picture()` | Take the screenshot now and show the window. |
| `CalibrationWindow.save()` | Write the current box into the settings and move on. |
| `CalibrationWindow.kind` | The `RegionKind` of the current step. |

## Tools

Scripts outside the package, run with `uv run python <path>`.

| Script | What it does |
|---|---|
| `tools/fetch_model.py` | Downloads the text recognition model and checks its checksum. |
| `tools/bench_capture.py` | Measures the time and CPU cost of capture and detection. |
| `.claude/skills/check-ui/standin_game.py` | Shows a screenshot in a window as a stand-in for the game. |
| `.claude/skills/detector-footage/cut_regions.py` | Cuts test regions out of full game frames. |
