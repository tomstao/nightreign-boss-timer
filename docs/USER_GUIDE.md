# User guide

> **No release has been published yet, and the tool has not been run against the real game.**
> Everything in this guide works today, in a program you build yourself or run from source (see
> [INSTALL.md](INSTALL.md)), except what is marked as planned. It has been checked against
> recorded fights played back in a window, not against the game itself: the game window's
> title, borderless mode and the cost in frame rate are still to be confirmed. Where the program
> and this guide disagree, that is a bug: please report it.

To install the tool, see [INSTALL.md](INSTALL.md).

## What the tool does

It watches the boss health bar on your screen and writes one row to a spreadsheet file for every
boss fight: when it happened, which boss, how long it took, and whether you finished it.

It only looks at the screen. It does not touch the game.

## Before you start

- Set the game to **windowed** or **borderless windowed**.
- Turn HDR off if detection is unreliable.
- Keep other overlays away from the boss health bar and from the middle of the screen where the
  defeat text appears.

## First-run setup

The first time the tool starts, a short guide opens. It has three steps, and **Skip setup** at
any step closes it for good without changing anything:

1. **Welcome**: what the tool does, and the language of the program.
2. **Game and regions**: whether the game window is found (**Check again** after starting the
   game), and **Calibrate regions**, described below.
3. **Basics**: the table your fights are saved under, the folder for `records.csv`, and the
   hotkeys that are set.

Everything in it can be changed later in the main window. To see the guide again, choose
**Show the setup guide again** on the Settings page.

The tool cannot find the health bar by itself yet, because its position depends on your
resolution. It starts with the usual positions for a 16:9 game image. To set them exactly, you
mark two areas once.

### 1. Health bar

1. Start a fight so that a boss health bar is on screen.
2. Press `Ctrl+Alt+C`, or choose **Calibrate regions** from the tray icon.
   A window opens with a screenshot of the game, taken at that moment.
3. A box is already drawn where the bar sits on a 16:9 game image. If it is not exactly on the
   bar, drag a box around the **whole bar, from its left end to its right end**, just the bar
   itself without the boss name above it. Drag a corner to resize the box, drag inside it to
   move it, or drag anywhere else to draw a new one. The arrow keys move the box one pixel at a
   time, and Shift with an arrow key resizes it one pixel at a time.
4. Watch the line at the bottom. It shows what the tool reads in the box as you move it, for
   example `Bar found, HP 100%`. If it says `No bar found in this box`, keep adjusting.
5. Choose **Save and next**.

If the screenshot was taken at a bad moment, choose **Retake screenshot**. The window steps
aside, takes a new screenshot of the game and comes back with your box unchanged. **Skip** goes
to the defeat text without changing the saved bar, and **Cancel** or Esc closes the window.

The boss name does not need its own box. The tool finds it from the position of the bar.

### 2. Defeat text

This is the gold text across the middle of the screen when a boss dies. It is on screen only
briefly, so you do not have to catch it live:

The second step of the calibration window starts with a box where the text appears on a 16:9
game image.

- If your game image is 16:9, you can choose **Save** straight away.
- Otherwise open calibration while the text is on screen, or use **Retake screenshot** at that
  moment, and drag a box around the text with a little room on each side. The line at the
  bottom says `Defeat text found` when the box is right.

Picking a frame from the last few seconds, or from a saved screenshot, is planned, so that you
will not have to catch the text live.

If the defeat text area is wrong, every fight is recorded as `incomplete`.

### Checking a calibration

The **Regions** page of the main window shows, for each of the two regions, whether it is
calibrated, with a button to calibrate just that one. Below that is what the tool sees right
now, re-read once a second: the pixels of the health bar region with `Bar detected: yes`, the
boss HP and the boss name as read, and the pixels of the defeat text region.

Use it with the game on screen and a boss bar showing. The main window is part of the screen
too, so keep it off the health bar and the middle of the game image while you check: on one
monitor, make the window small and move it to a corner.

### When to calibrate again

Calibrate again after changing the game's resolution, moving it to a monitor with a different
resolution, or changing Windows display scaling. The **Regions** page tells you when the game image
no longer has the size it had at calibration. Regions are saved as fractions of the game image,
so the same shape at another resolution usually still works: check the live preview.

## Everyday use

1. Start the tool. It sits in the system tray.
2. Check the **active table** shown on the overlay (see [Tables](#tables)).
3. Play. Recording is automatic.

| What happens in game | What the tool does |
|---|---|
| A boss health bar appears | starts the timer |
| The boss's HP reaches zero | stops the timer |
| The defeat text appears | saves the fight as `complete` |
| The bar empties, then disappears for 8 seconds | saves the fight as `complete`, with or without defeat text |
| The bar disappears for 8 seconds while the boss still has HP | saves the fight as `incomplete` |
| The bar comes back within those 8 seconds | carries on with the same fight |
| The bar appears and goes away without the boss losing HP | saves nothing |

The tool does not try to work out why a fight was not finished. Dying, leaving and running out of
time are all `incomplete`.

If you come back to a boss you damaged earlier, that is a new record. Its **start HP** column
shows how much health the boss had when you returned.

## The main window

Click the tray icon, or choose **Open main window** from its menu. Closing the window does not
stop the tool: it keeps running in the tray, and **Quit** in the tray menu ends it.

The bar at the bottom shows whether tracking is on, the active table, whether the game was
found and whether the regions are calibrated. Click **Tracking on** to pause or resume.

The window has six pages: **Records**, **Tables**, **Hotkeys**, **Regions**, **Settings** and
**About**.

## The overlay

A small see-through panel over the game. Mouse clicks pass through it.

The overlay is left out of screen captures, so that the tool never reads its own overlay as
part of the game. This also means it does not appear in screenshots, recordings or streams made
with other programs. On Windows 10 older than version 2004 this is not possible: there, keep
the overlay away from the health bar and the middle of the screen.

To record or stream the game with the overlay in the picture, turn on **Show the overlay in
screenshots and recordings** on the Settings page. The tool then sees the overlay too, so keep
it away from the boss health bar and from the middle of the screen, where the defeat text
appears. Where it starts, at the left edge, is clear of both. Turn the option off again when
you are done.

| Shows | When |
|---|---|
| the active table | while waiting for a fight |
| boss name, timer, boss HP % | during a fight |
| `COMPLETE` or `INCOMPLETE`, the time, your best time | for a few seconds after a fight |
| a warning such as `Regions not set` or `Paused` | when the tool cannot record |

The tray icon shows the same at a glance: a red bar while the tool is watching, gold during a
fight, grey when paused, and a gold dot when something needs your attention (the game was not
found, or finished fights are waiting because the records file is open in Excel).

To move the overlay, open the main window. While it is open the overlay has a frame and can be
dragged anywhere, including onto another monitor. Close the main window and it stays there, and
clicks pass through it again. **Reset position** on the Settings page puts it back.

The overlay can also be hidden completely, from the tray menu or with `Ctrl+Alt+O`: recording
works without it.

## Your records

Records are saved in `records.csv`, by default in `Documents\nightreign-boss-timer\`. Open it with
Excel or any spreadsheet program, or choose **Open records file in Excel** from the tray icon.

| Column | Meaning |
|---|---|
| `started_at` | date and time the fight began |
| `table` | the table that was active (see below) |
| `boss` | boss name as shown in game, or `unknown` if it could not be read. A reading one or two characters off a known name is corrected to it. |
| `language` | language the name was read in: `en`, `zh_CN` (Simplified) or `zh_TW` (Traditional). It is `zh` when the name is written the same in both kinds of Chinese, or is not in the list of known names. |
| `status` | `complete` or `incomplete` |
| `duration` | fight time as minutes:seconds |
| `duration_s` | the same in seconds, for sorting and charts |
| `start_hp_pct` | boss HP when the fight began; 100 for a full bar |
| `end_hp_pct` | boss HP when the fight ended; 0 for a kill |
| `level` | your level when the fight began, read from the emblem at the top left; empty if it could not be read |

| `boss_en` | the same boss in English, if the name is in the list of known names |
| `boss_zh_cn` | the same boss in Simplified Chinese |
| `boss_zh_tw` | the same boss in Traditional Chinese |

The tool knows the names of the game's bosses in all three languages. When the name it reads is
one of them, the record carries all three, whatever language your game is in. When it is not,
for example a boss added by a later update, `boss` holds the text as it was read and the three
translation columns stay empty.

The `level` and `boss_...` columns are new. A `records.csv` made by an older version gets them
the next time a fight is saved, left empty for the fights already in it.

**If the file is open in Excel when a fight ends**, Excel blocks other programs from writing to
it. The tool keeps the new rows in `records.pending.csv` next to it and adds them, in order, the
next time it can write. No fight is lost. Close and reopen the file in Excel to see new rows.

The main window's **Records** page shows the same data, newest first. Open it from the tray
menu with **Open records**.

- Filter by table, boss and status, or type in the search box to match a boss, a table or a
  date.
- Click a column heading to sort by it.
- A known boss is shown under its name in the language the program is set to, also for older
  records and for fights recorded with the game in another language. They count as one boss in
  the filter, the summary and the best time. Searching finds a boss by its name in any of the
  three languages.
- To delete records, select one or more rows (Ctrl or Shift for several) and press **Delete
  selected** or the Delete key, or right-click the selection. The tool asks first. Deleted rows
  are gone from `records.csv` for good, and it cannot be done while the file is open in Excel.
- Choose one boss to see a summary line: attempts, completes, your best time and your average.
  Best and average count only complete fights that began with the boss at full health.
- `incomplete` fights are shown in a different colour.
- A fight that ends while the page is open appears at once.
- **Open in Excel** and **Open folder** take you to the file.

Fights waiting in `records.pending.csv` are not listed until they have been written to
`records.csv`. Changing a row (moving it to another table, correcting the boss name, deleting
it) is planned; for now edit the file in Excel with the tool closed.

## Tables

A table is a name you give to a group of records, so that practice and real runs stay apart.

- Two tables exist from the start: **Arena** and **Normal**.
- Add your own under **Tables** in the main window, for example `No-hit practice`: type the
  name and choose **New table**. To rename a table, select it, type the new name and choose
  **Rename**. **Tables** is also reached from the tray menu: **Table**, **Manage tables**.
- Arena and Normal can be renamed but not deleted, so there is always somewhere to record.
- Records keep the table name they were saved with. Renaming or deleting a table does not
  change rows already in the file (renaming them along with the table is planned).
- One table is active at a time. Every fight is saved with the table that was active when it
  began.
- Switch tables from the tray menu (**Table**), on the **Tables** page (**Make active**, or
  double-click a table) or with a hotkey. The overlay always shows the
  active one, and confirms a switch for a few seconds. A switch during a fight applies from the
  next fight on.

All tables are saved in the same file. Use the `table` column to filter in Excel.

## Hotkeys

The defaults below work as soon as the tool runs, wherever the keyboard focus is.

To change one, open **Hotkeys** in the main window:

1. Select the action.
2. Click the field below the list and press the new shortcut, for example `Ctrl+Alt+E`. The
   field shows what you pressed. Press again to replace it.
3. Press Enter, or choose **Set**.

Backspace in the field, or **Clear**, leaves the action without a shortcut. Esc empties the
field. **Restore defaults** puts every shortcut back.

- A shortcut is one key, with any of Ctrl, Alt, Shift and Win: letters, digits, F1 to F24, the
  numpad digits, the navigation keys and punctuation.
- Each table has its own shortcut, at the bottom of the list.
- A shortcut already used by another action is refused, with the name of that action.
- A shortcut Windows will not hand over, usually because another program uses it, is marked
  `(not working)` in the list. Choose another, or close the other program and restart the tool.
- A single key such as `F8` is accepted with a warning: while the tool runs, that key no longer
  reaches the game.
- While the field has the keyboard, hotkeys are switched off, so pressing `Ctrl+Alt+P` there
  types it instead of pausing the tool.

| Action | Default |
|---|---|
| Pause or resume tracking | `Ctrl+Alt+P` |
| Next table | `Ctrl+Alt+T` |
| Switch to Arena / Normal | `Ctrl+Alt+1` / `Ctrl+Alt+2` |
| Show or hide the overlay | `Ctrl+Alt+O` |
| Open region calibration | `Ctrl+Alt+C` |
| Open the main window | not set |
| End the current fight now | not set |
| Discard the last record | not set |

**End the current fight now** saves the fight in progress as `incomplete` at that moment,
without waiting for the bar to go away. If the bar is still on screen afterwards, a new record
starts from the boss's current HP, and is dropped again if the boss loses no more.

**Discard the last record** removes the newest row from the file. Press it again within five
seconds to put the row back. It cannot remove a row while the file is open in Excel.

A hotkey works everywhere in Windows and takes that key combination away from the game while the
tool runs, so avoid keys you use to play.

## Settings worth knowing

Open **Settings** in the main window, or **Settings** in the tray menu. A change takes effect
and is saved as soon as you make it. There is no Save button.

| Setting | What it changes |
|---|---|
| Language | English, 简体中文 or 繁體中文, independent of the game language. The whole program switches at once. |
| Folder for records.csv | where fights are saved from now on. Records already saved stay in the old folder: move `records.csv` yourself to keep one file. **Use default** goes back to `Documents
ightreign-boss-timer`. |
| Seconds to wait after the bar disappears | how long the bar may be gone before a fight is closed (default 8, from 1 to 120) |
| Skip fights in which the boss lost no HP | whether walking past a boss is left out of the records (default on) |
| Screen checks per second during a fight | default 10, from 1 to 30; lower uses less CPU, higher times the end of a fight more exactly |

Planned and not there yet: starting with Windows, overlay opacity and size, the capture
method, and HDR compensation.

## Troubleshooting

| Problem | What to try |
|---|---|
| Fights are not recorded | Check the overlay for a warning. Open **Regions** and look at the live preview: it should show the bar and say `Bar detected: yes` during a fight. |
| A kill is saved as `incomplete` | The bar was hidden at the moment of the kill and no gold defeat text was seen. Check that the defeat text area is in the right place on the Regions page. Night bosses show a silver banner that the tool does not recognise yet; their kills are saved from the empty bar alone. |
| One fight became two records | The bar was hidden for longer than the wait, for example by a long look at the map. Raise **Seconds to wait after the bar disappears** on the Settings page. |
| Boss name is `unknown` | The name was covered when the bar appeared, or the text model was not downloaded (see [INSTALL.md](INSTALL.md#running-from-source)). The fight is still timed. Correcting a name in the program is planned; for now edit `records.csv`. |
| Times look a few seconds long or short | Recalibrate the health bar so the box covers the bar exactly, edge to edge. |
| The game stutters | Lower **Screen checks per second during a fight** on the Settings page. Choosing another capture method is planned. |
| New rows do not show in Excel | Excel does not reload an open file. Close and reopen it. |
| A hotkey does nothing | Open the Hotkeys page. A shortcut marked `(not working)` is held by another program: choose another one. |
| The overlay is missing from my recording | It is left out unless you turn on **Show the overlay in screenshots and recordings** on the Settings page: see [The overlay](#the-overlay). |

When reporting a problem, say which game language, resolution and window mode you use and whether
HDR is on, and attach a screenshot or a short clip, and the log file
`%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log`. Detection problems can only be fixed with
the frames that caused them. An **Export diagnostics** button on the About page is planned.

## What it does not do

- It does not read the game's memory, so it cannot know in-game time, damage numbers or your build.
- It does not work in exclusive fullscreen.
- It does not join a returning fight to the earlier one.
- It records one boss bar. Fights with two bars on screen at once are not handled yet.
- It has no controller bindings yet. Hotkeys are keyboard shortcuts.
