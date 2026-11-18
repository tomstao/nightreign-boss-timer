# UI design

Status, 2026-11-18: this is the design. All five surfaces are built. The wireframes show layout
and content, not final styling, and the last section lists where the program differs from them.
The [user guide](USER_GUIDE.md) describes the program as it is.

## Overview

The tool has five surfaces:

| Surface | When the user sees it | Purpose |
|---|---|---|
| Tray icon and menu | always, while the tool runs | quick switches without leaving the game |
| Overlay | in game | timer, boss, active table |
| Main window | on demand, from the tray | records, tables, hotkeys, regions, settings |
| Region calibration | first run, and when the game window changes | mark the health bar and defeat text |
| First-run setup | once | walks through the two regions and the basics |

Principles:

- **The game keeps focus.** Nothing the tool shows during play takes keyboard or mouse focus.
  Everything needed mid-session is reachable by hotkey or the tray.
- **Never silently not recording.** If the tool cannot track (regions missing, game not found,
  tracking paused), the tray icon and overlay say so.
- **Closing the main window hides it to the tray.** Quit is an explicit menu item.
- **The UI is available in English, 简体中文 and 繁體中文**, independent of the game language.

## Tables

A table is a named group of records. It replaces the fixed "game type" from the earlier plan.

- Two tables exist from the start: **Arena** and **Normal**. They can be renamed but not deleted,
  so there is always somewhere to record.
- The user can add tables with any name, for example "No-hit practice" or "Co-op with friends".
- Exactly one table is **active**. Each fight is stamped with the active table when it starts.
- Records stay in one `records.csv` with a `table` column, so Excel can filter or pivot by table.
  Renaming a table renames it in existing rows. Deleting a table keeps its rows.

## Tray menu

```
+--------------------------------+
|  Tracking: on            [x]   |
|  Table: Arena              >   |---> ( ) Normal
|--------------------------------|     (o) Arena
|  Show overlay            [x]   |     ( ) No-hit practice
|  Open records                  |     ---------------
|  Open records file in Excel    |     Manage tables...
|--------------------------------|
|  Calibrate regions...          |
|  Settings...                   |
|--------------------------------|
|  Quit                          |
+--------------------------------+
```

Tray icon states: tracking (normal), fight in progress (accent colour), paused (greyed),
needs attention (warning badge: regions missing, game not found, or records file not writable).

## Overlay

Small, transparent, click-through, always on top, excluded from screen capture unless the
user turns that off on the Settings page to record a video of it.

```
Idle                      Fight in progress              Just finished (shown ~8 s)

+------------------+      +------------------------+     +------------------------+
| Arena  - ready   |      | Arena                  |     | Arena      COMPLETE    |
+------------------+      | Tree Sentinel          |     | Tree Sentinel          |
                          | 01:23.4        HP 62%  |     | 02:41.3    best 02:10.9|
                          +------------------------+     +------------------------+
```

- Idle shows only the active table, so a wrong table is noticed before the fight, not after.
- "Just finished" shows `COMPLETE` or `INCOMPLETE`, the time, and the best complete time for that
  boss in the active table.
- Warnings replace the idle line: `Regions not set`, `Game not found`, `Paused`.
- Position is set by dragging while the main window is open (the overlay shows a visible frame
  then). It cannot be placed over a calibrated region.
- Options: show always / only during fights / never; opacity; scale; show HP %; show best time.

## Main window

A sidebar with six pages.

```
+----------------------------------------------------------------------+
| Nightreign Boss Timer                                      _  []  X  |
+-------------+--------------------------------------------------------+
|  Records    |                                                        |
|  Tables     |                (selected page)                         |
|  Hotkeys    |                                                        |
|  Regions    |                                                        |
|  Settings   |                                                        |
|  About      |                                                        |
+-------------+--------------------------------------------------------+
|  Tracking on  |  Table: Arena  |  Game: found  |  Regions: OK        |
+----------------------------------------------------------------------+
```

The status bar is always visible and each item is clickable (toggles tracking, opens the table
switcher, opens Regions).

### Records

```
 Table [ All        v]   Boss [ All          v]   Status [ All v]   [ Search... ]

 Date and time        Table   Boss            Status       Start   End    Time
 -------------------  ------  --------------  -----------  ------  -----  --------
 2026-11-17 21:12:05  Arena   Tree Sentinel   complete      62%     0%    01:15.8
 2026-11-17 21:04:33  Arena   Tree Sentinel   incomplete   100%    62%    02:41.3
 2026-11-16 22:40:10  Normal  unknown         complete     100%     0%    04:02.0

 3 records                      [ Open in Excel ]  [ Open folder ]
```

- Newest first. Columns sort on click. `incomplete` is visually distinct (colour plus text).
- Selecting a boss in the filter shows a summary line: attempts, completes, best and average time.
- Row actions (right-click): move to another table, correct the boss name, delete (asks first).
  Delete is also a button under the list and the Delete key, and works on several rows at once.
- An `unknown` boss row shows the saved name image, and correcting it teaches nothing automatic
  in the first release; it only fixes that row.

### Tables

```
 Active  Name               Records   Hotkey
 ------  -----------------  -------   ------------
  (o)    Arena                 128    Ctrl+Alt+1
  ( )    Normal                 14    Ctrl+Alt+2
  ( )    No-hit practice         9    (none)

 [ + New table ]   [ Rename ]   [ Delete ]        Next table: Ctrl+Alt+T
```

- The radio button sets the active table. Each table can have its own hotkey, and there is one
  "next table" hotkey that cycles.
- Names must be unique and non-empty. Delete is disabled for Arena and Normal.

### Hotkeys

```
 Action                          Shortcut           Controller
 ------------------------------  -----------------  ----------
 Toggle tracking                 Ctrl+Alt+P         (none)
 Next table                      Ctrl+Alt+T         (none)
 Switch to table: Arena          Ctrl+Alt+1         (none)
 Switch to table: Normal         Ctrl+Alt+2         (none)
 Show / hide overlay             Ctrl+Alt+O         (none)
 End current fight now           (none)             (none)
 Discard last record             (none)             (none)
 Open region calibration         Ctrl+Alt+C         (none)
 Open main window                (none)             (none)

 [ Restore defaults ]
```

- Click a shortcut cell, press the keys, Enter to accept, Esc to cancel, Backspace to clear.
- A shortcut already used by another action is rejected with the name of that action. A shortcut
  Windows refuses to register (taken by another program) is shown as failed, not silently ignored.
- Defaults use Ctrl+Alt combinations so they do not collide with game controls. Single keys are
  allowed but warned about, because a global hotkey takes the key away from the game.
- "End current fight now" writes the record as `incomplete` at that moment. "Discard last record"
  removes the most recent row, with a short undo on the overlay.
- Controller bindings (a button combination) are part of the design because the game is mostly
  played on a controller, but they ship after keyboard hotkeys.
- Hotkeys are global system hotkeys. Nothing is hooked inside the game.

### Regions

```
 Boss health bar      [ Calibrated ]   2560x1440    [ Recalibrate ]  [ Preview ]
 Defeat text          [ Not set    ]                [ Calibrate   ]

 Live preview
 +--------------------------------------------------------------+
 | (current pixels of the selected region, updated once a second) |
 +--------------------------------------------------------------+
 Bar detected: yes     HP: 62%     Name read: Tree Sentinel (en)
```

- The live preview and the three readouts are how the user confirms a calibration works before a
  real fight.
- If the game window size differs from the size at calibration, the row shows
  `Window changed - recalibrate` and tracking pauses.

### Settings

| Group | Options |
|---|---|
| General | UI language; start with Windows; start minimised to tray |
| Records | folder for `records.csv`; open folder; time format |
| Overlay | visibility mode; opacity; scale; show HP %; show best time; reset position |
| Capture | capture method (auto or a specific one); detection rate during a fight; game window (auto or pick) |
| Advanced | HDR compensation; save unknown boss name images; logging level |

### About

Version, licence, link to the repository, the safety statement, and **Export diagnostics**
(a ZIP with the log, settings without personal paths, and the last few region images).

## Region calibration

Opened from the tray, the Regions page, or a hotkey. It freezes a screenshot of the game window
and lets the user drag a box.

```
+------------------------------------------------------------------------+
|  Step 1 of 2 - Boss health bar                                         |
|  Drag a box around the whole bar, edge to edge.       [ Example image ]|
|                                                                        |
|                    (frozen screenshot of the game)                     |
|                                                                        |
|         +================================================+             |
|         |############################                    |  <- drag    |
|         +================================================+     handles |
|                                                                        |
|  [ Retake screenshot ]                  [ Cancel ]   [ Save and next ] |
+------------------------------------------------------------------------+
```

- The health bar step needs a boss bar on screen. The defeat text step needs the banner on screen,
  which is brief, so that step also accepts **a saved screenshot or a frame picked from the last
  30 seconds**, which the tool keeps in memory only while calibration is armed.
- After drawing, corner handles allow fine adjustment and arrow keys nudge by one pixel.
- Saving runs the detector once on the selection and reports the result (`Bar found, HP 100%`, or
  `No bar found in this box`), so a bad selection is caught immediately.

## First-run setup

A short sequence shown once, skippable at every step:

1. **Welcome**: what the tool does, the safety statement, UI language.
2. **Game check**: confirms the game window is found and not in exclusive fullscreen.
3. **Health bar**: calibration step 1.
4. **Defeat text**: calibration step 2, can be postponed. Until it is set, every record is
   `incomplete`, and the UI says so.
5. **Basics**: active table, records folder, hotkeys left at defaults with a link to change them.

## Notifications

| Event | Where | Text |
|---|---|---|
| Fight recorded | overlay, about 8 s | status, time, best |
| Table switched | overlay, about 3 s | `Table: Normal` |
| Tracking paused or resumed | overlay, about 3 s | `Paused` / `Tracking` |
| Record discarded | overlay, about 5 s | `Record discarded - undo: <hotkey>` |
| Records file locked by Excel | tray badge and status bar | `Records file is open elsewhere. 2 fights waiting to be saved.` |
| Window size changed | tray badge, overlay, Regions page | `Window changed - recalibrate` |

## Open questions

1. One CSV with a `table` column, or one CSV file per table. The design assumes one file.
2. Whether the best time shown on the overlay counts only fights that started at 100% HP.
   The design assumes yes, since a fight resumed at 62% is not comparable.
3. Whether the Records page needs charts (time per attempt for one boss) in the first release.
   The design leaves them out, because the CSV opens in Excel.

## Built so far, and where it differs

| Part of this design | State |
|---|---|
| Tray menu and icon states | built as designed, plus **Open main window**; a left click on the icon opens the main window |
| Overlay | built. See-through as a whole instead of pixel by pixel, with square corners, because Windows only then agrees to leave it out of screen captures |
| Overlay options | show or hide, and position by dragging. Not built: only during fights, opacity, scale, show HP, show best time |
| Overlay over a calibrated region | not prevented. It is left out of captures instead, on Windows 10 version 2004 and later |
| Main window, status bar | built as designed |
| Records page | filters, search, sorting, summary, open in Excel and folder. delete selected rows. A character column, **Set character** for the selected rows and **Delete incomplete** for the list shown, which the design did not have. Rows are chosen with a tick box per row and one in the heading for all rows shown, with the number chosen under the list. Not built: the other row actions (move, correct the boss name), and the saved image of an unknown name |
| Tables page | built. Names are typed into a field on the page instead of a dialog. Renaming does not rename existing rows yet. Table hotkeys are set on the Hotkeys page |
| Hotkeys page | built for the keyboard. The shortcut is pressed into a field below the list instead of into the cell. Not built: the Controller column |
| Regions page | built, with both regions previewed at once instead of a Preview button per row. A changed window size is pointed out but does not pause tracking |
| Settings page | language, records folder, the languages boss names are saved in, the character new records get, wait time, walk-past skipping, detection rate, overlay position. Not built: start with Windows, start minimised, time format, overlay opacity and scale, capture method, game window picker, HDR compensation, saving unknown name images, logging level |
| About page | built. Not built: Export diagnostics |
| Region calibration | built with the detector's reading shown as the box moves. Not built: the example image, and picking a saved screenshot or a recent frame for the defeat text |
| First-run setup | built as three steps instead of five: welcome, game and regions, basics |
| Notifications | fight recorded, table switched, paused and resumed, record discarded. Not built: the records-file-locked message with its count (the tray icon shows a dot instead) |
