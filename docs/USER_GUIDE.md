# User guide

> **The program described here is not released yet.** This guide is written ahead of the first
> release from the agreed design, so the behaviour can be checked before it is built. It is
> updated with every change that affects users. Where the program and this guide disagree once a
> release exists, that is a bug: please report it.
>
> **What works today** is the overlay with a tray icon (pause, switch table, hide overlay, open
> the records file, calibrate regions, quit) and the command-line version, both described in
> [INSTALL.md](INSTALL.md#running-from-source). It follows the recording rules under
> [Everyday use](#everyday-use) and writes the file described under [Your records](#your-records).
> Region calibration works as described under [First-run setup](#first-run-setup), from the tray
> menu. Until you calibrate, the tool uses the usual positions for a 16:9 game image. The
> calibration hotkey, picking a recent frame, the main window, tables beyond one name, hotkeys
> and settings are not built yet.

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

The tool cannot find the health bar by itself yet, because its position depends on your
resolution. You mark two areas once.

### 1. Health bar

1. Start a fight so that a boss health bar is on screen.
2. Choose **Calibrate regions** from the tray icon (a hotkey, default `Ctrl+Alt+C`, is planned).
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
| The bar disappears for 8 seconds with no defeat text | saves the fight as `incomplete` |
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

So far the window has the **Records**, **Tables**, **Regions**, **Settings** and **About**
pages. Hotkeys are being added.

## The overlay

A small see-through panel over the game. Mouse clicks pass through it.

| Shows | When |
|---|---|
| the active table | while waiting for a fight |
| boss name, timer, boss HP % | during a fight |
| `COMPLETE` or `INCOMPLETE`, the time, your best time | for a few seconds after a fight |
| a warning such as `Regions not set` or `Paused` | when the tool cannot record |

The tray icon shows the same at a glance: a red bar while the tool is watching, gold during a
fight, grey when paused, and a gold dot when something needs your attention (the game was not
found, or finished fights are waiting because the records file is open in Excel).

Open the main window to drag the overlay somewhere else. It can also be hidden completely:
recording works without it.

## Your records

Records are saved in `records.csv`, by default in `Documents\nightreign-boss-timer\`. Open it with
Excel or any spreadsheet program, or choose **Open records file in Excel** from the tray icon.

| Column | Meaning |
|---|---|
| `started_at` | date and time the fight began |
| `table` | the table that was active (see below) |
| `boss` | boss name as shown in game, or `unknown` if it could not be read |
| `language` | language the name was read in: `en`, or `zh` for Chinese. Simplified and Traditional are not told apart yet. |
| `status` | `complete` or `incomplete` |
| `duration` | fight time as minutes:seconds |
| `duration_s` | the same in seconds, for sorting and charts |
| `start_hp_pct` | boss HP when the fight began; 100 for a full bar |
| `end_hp_pct` | boss HP when the fight ended; 0 for a kill |

**If the file is open in Excel when a fight ends**, Excel blocks other programs from writing to
it. The tool keeps the new rows in `records.pending.csv` next to it and adds them, in order, the
next time it can write. No fight is lost. Close and reopen the file in Excel to see new rows.

The main window's **Records** page shows the same data, newest first. Open it from the tray
menu with **Open records**.

- Filter by table, boss and status, or type in the search box to match a boss, a table or a
  date.
- Click a column heading to sort by it.
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

Set them under **Hotkeys** in the main window: click a shortcut, press the keys, press Enter.

| Action | Default |
|---|---|
| Pause or resume tracking | `Ctrl+Alt+P` |
| Next table | `Ctrl+Alt+T` |
| Switch to Arena / Normal | `Ctrl+Alt+1` / `Ctrl+Alt+2` |
| Show or hide the overlay | `Ctrl+Alt+O` |
| Open region calibration | `Ctrl+Alt+C` |
| End the current fight now | not set |
| Discard the last record | not set |
| Open the main window | not set |

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

Planned and not there yet: starting with Windows, overlay opacity, size and position, the
capture method, and HDR compensation.

## Troubleshooting

| Problem | What to try |
|---|---|
| Fights are not recorded | Check the overlay for a warning. Open **Regions** and look at the live preview: it should show the bar and say `Bar detected: yes` during a fight. |
| Every fight is `incomplete` | The defeat text area is not set, or its box is too small. Recalibrate it. |
| One fight became two records | The bar was hidden for longer than the wait window, for example by a long look at the map. Raise the wait window in Settings. |
| Boss name is `unknown` | The name was covered when the bar appeared, or the boss is not in the name list yet. The fight is still timed. Correct the name on the Records page. |
| Times look a few seconds long or short | Recalibrate the health bar so the box covers the bar exactly, edge to edge. |
| The game stutters | Lower the detection rate, or try another capture method under Settings, Capture. |
| New rows do not show in Excel | Excel does not reload an open file. Close and reopen it. |

When reporting a problem, use **About, Export diagnostics** and attach the ZIP. Detection problems
can only be fixed with the frames that caused them.

## What it does not do

- It does not read the game's memory, so it cannot know in-game time, damage numbers or your build.
- It does not work in exclusive fullscreen.
- It does not join a returning fight to the earlier one.
- It records one boss bar. Fights with two bars on screen at once are not handled yet.
