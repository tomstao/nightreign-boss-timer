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
| `FightTracker.end_now()` | End the current fight as incomplete, on the user's request. |
| `FightTracker.in_fight` | True from the confirmed start until the outcome. |
| `FightTracker.started_at` | The tracker-clock time the current fight began. |
| `FightTracker.hp` | The current smoothed HP, or `None`. |
| `FightTracker.watching_for_defeat` | True while the defeat text region needs to be read. |
| `FightOutcome` | `status`, `started_at`, `duration_s`, `start_hp_pct`, `end_hp_pct`. |
| `FULL_HP` | A reading at or above this is written as 100%. |

### `nightreign_boss_timer.boss_names`

The boss names the game uses, in English, Simplified Chinese and Traditional Chinese, and a
lookup that finds a reading in them.

| Name | What it is |
|---|---|
| `load()` | The `BossNames` list packed with the program (`boss_names.json`). |
| `BossNames(rows)` | A list built from `[English, Simplified, Traditional]` rows. |
| `BossNames.lookup(text)` | The `BossMatch` a reading stands for, or `None`. Ignores case, spaces and punctuation, and repairs one wrong character in names of 4 or more, two in names of 8 or more. |
| `BossMatch` | `name` (as the game writes it), `language`, `en`, `zh_cn`, `zh_tw`. A translation is empty when the list has more than one. |
| `LANGUAGES`, `CHINESE` | The values of `BossMatch.language`: `en`, `zh_CN`, `zh_TW`, and `zh` for a name written the same in both kinds of Chinese. |

### `nightreign_boss_timer.level`

Finds the player's level digits in the emblem at the top left, and settles on a level from
several readings.

| Name | What it is |
|---|---|
| `find_digits(region)` | A tight crop around the white digits in the level box, or `None` if there are none. |
| `parse_level(text)` | The level a reading stands for, `MIN_LEVEL` to `MAX_LEVEL`, or `None`. |
| `LevelVote` | Collects readings for one fight: `add(text)`, `miss()` for a look that found no digits, `settled`, `level`. |
| `MIN_LEVEL`, `MAX_LEVEL` | The levels the game has. |
| `AGREE`, `MAX_READS`, `MAX_MISSES` | When the vote stops asking for readings. |

### `nightreign_boss_timer.ocr`

Reads one line of text, the boss name, with a small ONNX model on the CPU.

| Name | What it is |
|---|---|
| `NameReader(model_path)` | Loads the model. Raises `FileNotFoundError` if it was not downloaded. |
| `NameReader.read(region, digits_only=False)` | Returns a `TextReading`. With `digits_only` the answer can only hold the digits 0 to 9. |
| `TextReading` | `text` and `confidence`. |
| `default_model_path()` | Where the model file is: `NBT_MODEL_DIR` if set, else the copy packed into the packaged program, else the user's local app data. |
| `bundled_model_path()` | The copy packed into the packaged program, or `None` when running from source. |
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
| `DEFAULT_LEVEL` | The middle of the level emblem on a 16:9 image. |
| `level_region(window, level)` | Screen pixels holding the player's level. |

### `nightreign_boss_timer.capture`

Copies small regions of the screen into arrays with GDI. Windows only.

| Name | What it is |
|---|---|
| `enable_dpi_awareness()` | Call once at start, so coordinates mean real pixels. |
| `exclude_from_capture(handle, exclude=True)` | Ask Windows to leave one of this program's windows out of every screen capture, or with `exclude=False` to put it back. False if refused. |
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
| `FightRecord` | One fight: `started_at`, `table`, `boss`, `language`, `status`, `duration_s`, `start_hp_pct`, `end_hp_pct`, `level` (`None` if unread), and `boss_2`, `language_2`, `boss_3`, `language_3` for the same boss in a second and third language (empty if not asked for). |
| `Status` | `COMPLETE` or `INCOMPLETE`. |
| `RecordStore(path)` | The CSV file. |
| `RecordStore.append(record)` | Save a record. Returns `False` if it had to be held because the file is locked. |
| `RecordStore.read_all()` | All saved records, oldest first. |
| `RecordStore.flush_pending()` | Try to write held rows. |
| `RecordStore.remove_last()` | Take the most recent record out and return it. Raises `PermissionError` if the file is locked. |
| `RecordStore.remove(records)` | Take these records out of the file. Returns how many were removed. Raises `PermissionError` if the file is locked. |
| `RecordStore.pending_count()` | How many rows are held. |
| `RecordStore.set_path(path)` | Save to another file from now on. |
| `RecordStore.ensure_file()` | Create the file with its header row if it is missing. |
| `format_duration(seconds)` | `mm:ss.s`. |
| `COLUMNS` | The CSV columns, in order. |

### `nightreign_boss_timer.record_view`

Chooses which records to show and sums them up. No drawing.

| Name | What it is |
|---|---|
| `filter_records(records, table, boss, status, search)` | The records that pass every filter, newest first. |
| `summarise(records)` | A `Summary` of a set of fights. |
| `Summary` | `attempts`, `completes`, `best_s`, `average_s`. The times count only complete fights that began at full health. |
| `names_in(records)` | The table names and boss keys that appear, each sorted. |
| `translations(record)` | The boss in English, Simplified and Traditional Chinese, looked up from the name saved. |
| `boss_key(record)`, `key_of(name)` | What a boss is grouped under: its English name if known, else the name as read. |
| `boss_label(record, language)` | The boss in a UI language, or as it was read. |
| `label_of(name, language)` | The same for a bare name, as the overlay has during a fight. |
| `ALL` | The filter value that lets everything through. |

### `nightreign_boss_timer.settings`

The user's settings, kept in one JSON file. Loading never fails.

| Name | What it is |
|---|---|
| `Settings` | All settings: language, tables, active table, records folder, timing, regions, hotkeys. |
| `Settings.record_languages()` | The languages a boss name is saved in: the user's choice, or the UI language until they choose. |
| `Settings.set_name_language(language, on)` | Start or stop saving the name in a language. `False` if it would leave none or exceed `MAX_NAMES`. |
| `NAME_LANGUAGES`, `MAX_NAMES` | The languages a name can be saved in, and how many one record holds. |
| `Settings.add_table(name)` | Add a table. Raises `TableError` for an empty or duplicate name. |
| `Settings.rename_table(old, new)` | Rename a table. |
| `Settings.delete_table(name)` | Delete a table. Built-in tables cannot be deleted. |
| `Settings.set_active_table(name)` | Choose the table new fights are saved under. |
| `Settings.next_table()` | Make the next table active, wrapping around. |
| `Settings.table_names()` | Names in display order. |
| `Table` | `name`, `builtin`, `hotkey`. |
| `TableError` | A table change that is not allowed. Carries `reason` (`missing`, `empty`, `duplicate`, `builtin`) and `name`. |
| `load(path)` | Read the file. Missing or damaged files give defaults. |
| `save(settings, path)` | Write the file safely. |
| `default_settings_path()` | `%APPDATA%\nightreign-boss-timer\settings.json`. |
| `DEFAULT_HOTKEYS` | Action name to default shortcut. |
| `UI_LANGUAGES` | The supported UI languages. |

### `nightreign_boss_timer.hotkeys`

Shortcuts such as `Ctrl+Alt+P`: reading them, checking them, keeping them registered. No Qt and
no Windows calls of its own.

| Name | What it is |
|---|---|
| `normalise(shortcut)` | The shortcut in its standard spelling, or an empty string if it is not one. |
| `parse(shortcut)` | A `Hotkey`, or `None`. |
| `Hotkey` | `modifiers` and `key`, as Windows wants them. |
| `has_modifier(shortcut)` | False for a single key such as `F5`. |
| `bindings(settings)` | Action to shortcut for every action that has one. Table actions are `table:<name>`. |
| `conflict(settings, action, shortcut)` | The other action already using this shortcut, or an empty string. |
| `HotkeyManager(register, unregister)` | Keeps registered hotkeys equal to a set of bindings. |
| `HotkeyManager.apply(wanted)` | Register what is new or changed, release what is gone. |
| `HotkeyManager.action_for(hotkey_id)` | The action a pressed hotkey stands for. |
| `HotkeyManager.release_all()` | Give every hotkey back. |
| `HotkeyManager.failed` | Actions whose shortcut Windows refused. |
| `KEYS` | Key name to virtual-key code. |
| `MODIFIERS` | Modifier name to flag, in writing order. |
| `TABLE_PREFIX` | `table:`, the start of a table action's name. |

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
| `Engine.end_fight()` | Ask for the fight in progress to be ended as incomplete. The next step does it. |
| `Engine.probe()` | Read both regions once, outside the watch loop. Returns a `Probe`, or `None` if the game is not found. |
| `Probe` | `window` size, `bar_image`, `bar`, `text_image`, `defeat`, `name`. |
| `StepResult` | `snapshot`, `record` (set when a fight just ended), `saved`, `delay_s` (how long to wait before the next step). |
| `Snapshot` | What to show now: `state`, `table`, `boss`, `hp`, `elapsed_s`. |
| `State` | `PAUSED`, `NO_GAME`, `IDLE`, `FIGHT`. |
| `Screen` | The interface the engine needs from the screen: `find_window(title)` and `grab(box)`. |
| `NameSource` | The interface for reading a name: `read(region)`. |
| `records_path(settings)` | Where `records.csv` is for these settings. |
| `to_record(outcome, table, now, wall_now, boss, level, languages)` | Turn a tracker outcome into a `FightRecord`. A known boss gets its name in each of `languages`, up to three; any other keeps the text as read. |
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
| `App` | Builds the engine, controller, overlay, tray and windows, and drives the engine with a timer. `settings_path` replaces the usual settings file. |
| `main()` | Parses `--title`, `--records`, `--settings` and `--self-test`, starts logging and runs the Qt event loop. |
| `self_test(application)` | Start everything for a moment against temporary files and return 0 if every part came up. Run on each freshly built program. |
| `start_logging()` | Write warnings and crashes to `log_path()`. The packaged program has no console. |
| `log_path()` | `%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log`. |

### `nightreign_boss_timer.ui.controller`

Every action the user can take, shared by the tray, the windows and the hotkeys.

| Name | What it is |
|---|---|
| `Controller(settings, translate, store)` | Holds the settings and the on/off state. `settings_path` and `opener` can be replaced for tests. |
| `Controller.changed` | Signal: something shown in a menu or window is now different. |
| `Controller.notice` | Signal with a short message for the overlay. |
| `Controller.calibration_requested` | Signal: open the calibration window. |
| `Controller.records_changed` | Signal: a fight was saved or records were edited. |
| `Controller.set_tracking(on)` | Pause or resume. Also `toggle_tracking()`. |
| `Controller.set_overlay_visible(on)` | Show or hide the overlay. Also `toggle_overlay()`. |
| `Controller.set_table(name)` | Switch the active table and save. Also `next_table()`. |
| `Controller.add_table(name)` | Add a table. Returns an error message in the user's language, or an empty string. Also `rename_table(old, new)` and `delete_table(name)`. |
| `Controller.hotkey_actions()` | Every action that can have a shortcut, in display order. |
| `Controller.action_label(action)` | An action's name in the user's language. |
| `Controller.hotkey_of(action)` | An action's shortcut, or an empty string. |
| `Controller.set_hotkey(action, shortcut)` | Set or clear a shortcut. Returns a refusal or a warning in the user's language, or an empty string. |
| `Controller.restore_default_hotkeys()` | Put every shortcut back as it was at first. |
| `Controller.refresh_hotkeys()` | Register the settings' shortcuts with Windows through `hotkey_applier` and update `failed_hotkeys`. |
| `Controller.suspend_hotkeys(suspended)` | Stop hotkeys firing while a shortcut is typed. Emits `hotkeys_suspended`. |
| `Controller.run_action(action)` | Do what a hotkey stands for. Returns False for an unknown action. |
| `Controller.end_fight()` | Ask for the fight in progress to be ended now. Emits `end_fight_requested`. |
| `Controller.discard_last()` | Remove the most recent record. Again within `UNDO_SECONDS` puts it back. |
| `Controller.set_language(language)` | Switch the UI language. Everything is redrawn at once. |
| `Controller.set_records_folder(folder)` | Save records elsewhere from now on. Empty means the default folder. |
| `Controller.set_overlay_position(position)` | Remember where the overlay was put. `None` resets it. |
| `Controller.window_shown` | Signal: the main window was shown (True) or hidden (False). |
| `Controller.set_option(name, value)` | Change `wait_window_s`, `skip_walk_pasts`, `fight_rate` or `overlay_in_captures`. |
| `Controller.set_name_language(language, on)` | Start or stop saving the boss name in a language. |
| `Controller.delete_records(records)` | Delete these records for good. Returns an error message, or `""`. |
| `Controller.open_records_file()` | Open `records.csv` in the program Windows uses for it. |
| `Controller.open_records_folder()` | Open the folder that holds it. |
| `Controller.calibrate(region)` | Ask for the calibration window, at `bar`, `defeat_text` or the first step. |
| `Controller.probe` | Set by the app to `Engine.probe`. `None` when there is no screen to read. |
| `Controller.show_setup()` | Ask for the first-run setup guide. Emits `setup_requested`. |
| `Controller.finish_setup()` | Remember that setup was finished or skipped. |
| `Controller.show_window(page)` | Ask for the main window, optionally at a page key such as `records`. |
| `Controller.window_requested` | Signal carrying that page key. |
| `Controller.set_state(state)` | Told by the app after every engine step. Emits `state_changed` when it differs. |
| `Controller.state` | The engine's last `State`. |
| `Controller.calibrated` | True once the health bar region has been saved. |
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
| `Overlay.set_position(position)` | Put its top-left corner somewhere, or back at `DEFAULT_POSITION` with `None`. |
| `Overlay.set_movable(movable, hint)` | Let the user drag it, with a frame, or give clicks back to the game. |
| `Overlay.set_in_captures(shown)` | Let screenshots and recordings show it, or keep it out of them (the start). |
| `Overlay.moved` | Signal with the new corner after a drag. |
| `DEFAULT_POSITION` | Where the overlay starts. |
| `Overlay.hidden_from_capture` | True once Windows has agreed to keep it out of screen captures. |

### `nightreign_boss_timer.ui.tray`

The tray icon and its menu.

| Name | What it is |
|---|---|
| `Tray(controller, quit_app)` | Builds the icon and menu, and rebuilds the menu when the controller changes. |
| `Tray.set_state(state)` | Change the icon. |
| `Tray.rebuild()` | Rebuild the menu from the settings. |
| `IconState` | `TRACKING`, `FIGHT`, `PAUSED`, `ATTENTION`. |
| `make_icon(state)` | The icon picture for a state. |

### `nightreign_boss_timer.ui.global_hotkeys`

Registers hotkeys with Windows (`RegisterHotKey`) and announces presses.

| Name | What it is |
|---|---|
| `GlobalHotkeys` | Owns a hidden window for hotkey messages and a `HotkeyManager`. |
| `GlobalHotkeys.apply(settings)` | Make the registered hotkeys match the settings. |
| `GlobalHotkeys.triggered` | Signal carrying the action of a pressed hotkey. |
| `GlobalHotkeys.failed` | Actions whose shortcut Windows refused. |
| `GlobalHotkeys.pressed(hotkey_id)` | Called when Windows reports a press. |
| `GlobalHotkeys.close()` | Release every hotkey. |

### `nightreign_boss_timer.ui.hotkeys_page`

The Hotkeys page: every action with its shortcut, and a field to press a new one into.

| Name | What it is |
|---|---|
| `HotkeysPage` | The page. |
| `HotkeysPage.selected()` | The selected action, or an empty string. |
| `HotkeysPage.set_shortcut()` | Give the selected action the shortcut shown in the field. Also `clear_shortcut()` and `restore_defaults()`. |
| `ShortcutEdit` | A field that shows the shortcut pressed into it. Signals `accepted`, `cleared`, `focus_changed`. |
| `key_name(key, modifiers, native_code)` | A pressed key's name as shortcuts spell it, or an empty string. |

### `nightreign_boss_timer.ui.main_window`

The main window: sidebar, pages, status bar. Closing it only hides it.

| Name | What it is |
|---|---|
| `MainWindow(controller, pages)` | The window. Without `pages` it uses `default_pages`. |
| `MainWindow.show_page(key)` | Bring the window up, on the page with this key if there is one. |
| `MainWindow.refresh()` | Redraw every text from the settings, in the current language. |
| `default_pages(controller)` | The pages in sidebar order. Add a new page here. |

### `nightreign_boss_timer.ui.pages`

What every page has in common, and the About page.

| Name | What it is |
|---|---|
| `Page` | Base class. Set `key` (the sidebar text is the translation of `page.<key>`) and write `refresh()`. |
| `Page.refresh()` | Redraw from the settings. Called when the page is shown and on every controller change. |
| `AboutPage` | Version, licence, repository link and the safety statement. |
| `REPOSITORY_URL` | Where the project lives. |

### `nightreign_boss_timer.ui.records_page`

The Records page: every saved fight with filters, sorting and a per-boss summary.

| Name | What it is |
|---|---|
| `RecordsPage` | The page. Reads the records file on `refresh()`. |
| `RecordsPage.shown_records()` | The records that pass the filters as they are set now. |
| `RecordsPage.selected_records()` | The records of the selected rows. |
| `RecordsPage.delete_selected()` | Delete the selected records, after asking. `ask` in the constructor replaces the question window. |
| `COLUMNS` | The table's columns, in order. |

### `nightreign_boss_timer.ui.regions_page`

The Regions page: calibration status, and a live preview of both regions.

| Name | What it is |
|---|---|
| `RegionsPage` | The page. Reads the screen once a second, only while it is shown. |
| `RegionsPage.update_preview()` | Read both regions now and show them with what was read. |
| `PREVIEW_MS` | Time between two readings. |

### `nightreign_boss_timer.ui.settings_page`

The Settings page. Every change is applied and saved at once.

| Name | What it is |
|---|---|
| `SettingsPage(controller, choose_folder)` | The page. `choose_folder` shows the folder dialog and can be replaced for tests. |

### `nightreign_boss_timer.ui.setup_window`

First-run setup: welcome and language, game and regions, basics. Shown once.

| Name | What it is |
|---|---|
| `SetupWindow(controller, choose_folder)` | The guide. `choose_folder` shows the folder dialog and can be replaced for tests. |
| `SetupWindow.start()` | Open at the first step. |
| `SetupWindow.go_to(step)` | Show a step, counted from zero. |
| `SetupWindow.check_game()` | Look for the game window now and say what was found. |
| `SetupWindow.finish()` | Close and remember, for Finish and for Skip setup. |
| `SetupWindow.refresh()` | Redraw every text in the current language. |
| `STEPS` | The number of steps. |

### `nightreign_boss_timer.ui.tables_page`

The Tables page: add, rename, delete, and choose the active table.

| Name | What it is |
|---|---|
| `TablesPage` | The page. |
| `TablesPage.selected()` | The name of the selected table, or an empty string. |
| `TablesPage.add()` | Add a table named by the text field. Also `rename()`, `delete()` and `make_active()` for the selected table. |
| `ACTIVE_MARK` | The mark shown beside the active table. |

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
| `CalibrationWindow.start(region)` | Take a screenshot and open at the first step, or at the step for `bar` or `defeat_text`. |
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
| `tools/build_exe.py` | Builds the Windows program with PyInstaller, collects licence files, runs its self-test and packs the release ZIP. |
| `packaging/launcher.py` | The file the packaged program starts with. |
| `.claude/skills/check-ui/standin_game.py` | Shows a screenshot in a window as a stand-in for the game. |
| `.claude/skills/detector-footage/cut_regions.py` | Cuts test regions out of full game frames. |
