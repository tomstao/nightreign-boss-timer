# Plan

Status: draft, 2026-11-17. Nothing is implemented yet.

## Goal

A Windows tool that watches the Nightreign boss health bar on screen and records how long each
boss fight takes, from the moment the bar appears to the moment the boss dies, without lowering
the game's frame rate.

Supported game languages for now: English, Simplified Chinese, Traditional Chinese.

## Non-goals

- Reading game memory, injecting code, or modifying game files.
- Exclusive fullscreen support.
- In-game time. We record wall-clock time only.
- Other languages, until the three above work.

## Recording rules

Set by the project owner on 2026-11-17. These override anything else in this plan.

1. **Every fight is one record, stored by date and time.** The record's key is the local date and
   time the fight started. The history is listed newest first.
2. **Bar gone for a while with no defeat text: the record is `incomplete`.** The status is stored
   and shown in the history. The record keeps the elapsed time and the boss HP % that was left.
   The tool does not try to tell why: the player may have died, left, or only walked past the
   boss. All of those are simply `incomplete`.
3. **Bar appears already below full: a new record, with its starting percentage.** This is the case
   of coming back to a boss fought earlier. The record stores the HP % the bar started at.
4. **No continuation.** A returning fight is never joined to the earlier incomplete record. Each
   appearance of the bar stands alone.

7. **The defeat text is the same in every game language.** Confirmed by the project owner. It is
   detected by its look, not read as text, and needs no language handling.

8. **The timer stops when the boss's HP reaches zero.** The seconds the empty bar stays on screen
   during the death animation are not counted. For an `incomplete` record the time runs to the
   last moment the bar was seen.
9. **Walk-past records are skipped.** If the boss's HP did not change between the bar appearing
   and disappearing, nothing is written.
10. **Every record shows the boss HP % when the fight began**, in its own column. A full bar is
    written as 100. A boss met already damaged is written with its actual percentage.

How the plan applies these: after the bar disappears the tool waits a short time (the "wait
window", a setting, 8 seconds to start with). Defeat text seen in that window makes the record
`complete`. No defeat text by the end of it makes the record `incomplete`. If the bar comes back
inside the window, it is treated as the same fight still going on, since the bar was only hidden
for a moment. A bar that appears after the window has closed is a new record (rule 4).

## First-run setup

Set by the project owner on 2026-11-17. At this stage nothing is located automatically. On first
use the user marks two regions by hand, and the tool does not start tracking until both exist.

| Region | What the user selects | Used for |
|---|---|---|
| Boss health bar | the full bar, edge to edge, while a boss bar is on screen | bar presence, HP %, and the boss name line, which is derived from the bar's position |
| Defeat text | the area where the boss-defeated banner appears | deciding `complete` |

- Calibration is a screenshot with a drag-to-select box, opened from the tray menu or a hotkey,
  the same pattern the example app uses.
- Regions are saved in the settings file as fractions of the game window, so moving the window
  keeps them valid. Changing resolution, monitor or display scaling needs a new calibration, and
  the tool says so when the window size no longer matches the saved one.
- Each region shows a live preview after saving, so a wrong selection is visible before a fight.
- If the derived name line turns out unreliable in M0 footage, it becomes a third region.
- Automatic regions for 16:9 are a later improvement, not part of the first release.

5. **Records live in a spreadsheet-friendly file.** The store is a CSV file that opens directly in
   Excel. See Records under Design.
6. **Every record belongs to a table.** `Arena` and `Normal` exist from the start, and the user can
   add tables with their own names. The main use is training records from the Boss Arena mod, so
   `Arena` is the default. Hotkeys are user-configurable. The screens are in [UI.md](UI.md).

### Record fields

| Field | Example | Notes |
|---|---|---|
| started_at | 2026-11-17 21:04:33 | local date and time, the record key |
| table | Arena | the active table when the fight starts: `Arena`, `Normal`, or a user-defined name |
| boss | Tree Sentinel | lexicon id plus the name as read, or `unknown` |
| language | zh_CN | language the name was read in |
| status | `complete` / `incomplete` | |
| duration | 02:41.3 | bar first seen to HP zero, or to bar last seen if `incomplete` (rule 8) |
| start_hp_pct | 100 | boss HP % when the bar appeared; below 100 means the boss was already damaged (rules 3 and 10) |
| end_hp_pct | 0 | HP % left when the bar was last seen |

### How the history reads

| Date and time | Type | Boss | Status | Start HP | End HP | Time |
|---|---|---|---|---|---|---|
| 2026-11-17 21:12:05 | Arena | Tree Sentinel | complete | 62% | 0% | 01:15.8 |
| 2026-11-17 21:04:33 | Arena | Tree Sentinel | incomplete | 100% | 62% | 02:41.3 |

## Performance budget

| Metric | Target |
|---|---|
| CPU, averaged over a fight | under 1% of total CPU |
| GPU | no inference on the GPU, only the ROI readback |
| Memory | under 200 MB |
| Game FPS impact | not measurable (within run-to-run noise) with the tool on vs off |
| Timing error | within 0.2 s of a frame-by-frame review of a recording |

These are targets to measure against in M1 and M5, not results.

## Design

```
capture (ROI only) -> bar detector -> fight state machine -> timer -> record store
                          |                  |                           |
                          |                  +-> OCR on demand -> lexicon match (boss, language)
                          +-> HP fill ratio                              |
                                                                    overlay HUD
```

### Capture

- Find the game window and map the user-calibrated regions (see First-run setup) to pixels.
- Copy only small regions: the boss bar strip and the name line above it during a fight, and the
  defeat text region for a few seconds after the bar disappears.
- Backend behind one interface. Candidates: DXGI Desktop Duplication, WGC, GDI BitBlt.
  This PC runs Windows 10 19045, where WGC is expected to draw a yellow capture border, so DXGI
  duplication or BitBlt is the likely default here. M1 measures and decides.
- Adaptive rate: about 2 Hz while no bar is visible, about 10 Hz during a fight.

### Bar detector (every sample, cheap)

- Colour mask plus shape check on the bar strip decides "boss bar present".
- Scanning the bar row gives the HP fill ratio, 0.0 to 1.0.
- Pure NumPy on a strip a few hundred pixels wide. No model.

### OCR (rare, on demand)

- Runs only when the bar has just appeared: recognition-only on the name crop, a few attempts
  with majority vote, then stops for the rest of the fight.
- Output is fuzzy-matched against a trilingual boss lexicon. The matched entry gives both the
  boss identity and the game language, so no language setting is needed.
- Engine: PP-OCRv5 mobile recognition model on ONNX Runtime, CPU, one thread.
- If no lexicon entry matches, the fight is still timed and stored as "unknown" with the name crop
  saved for later.

### Fight state machine

| State | Enter when | Notes |
|---|---|---|
| Idle | no bar | slow polling |
| Pending | bar seen | must persist about 300 ms to count |
| Fighting | bar confirmed | start time backdated to first sight, start HP % stored, OCR fires |
| Waiting | bar gone | watch the defeat text region for the wait window; back to Fighting if the bar returns |
| Complete | defeat text seen while Waiting | end time is the moment HP reached zero (rule 8) |
| Incomplete | wait window ended with no defeat text | end time is the last sight of the bar; remaining HP % stored |
| Skipped | wait window ended and HP never changed | nothing written (rule 9) |

Details that follow from the rules and the first clip:

- **HP zero** is the first sample where the red part of the bar is gone while the empty bar is
  still visible. The empty bar staying on screen for several seconds after a kill is what makes
  this moment readable.
- **Full bar reads as 100.** A full bar measured 99.1% in the first clip, because its right tip
  fades out. A start reading at or above 98% is written as 100.
- **"HP never changed"** means the highest and lowest smoothed readings of the fight differ by
  less than 1 percentage point. The threshold is a setting.
- If the defeat text appears but HP zero was never observed (the bar was hidden at that moment),
  the end time falls back to the last sight of the bar.

The defeat text is detected by colour: a count of gold pixels in its calibrated region, which was
zero for a whole fight and a steady 10% while the text showed (see
[observations](observations.md)). No text recognition and no language handling. Both end states
write the record and return to Idle. There is no attempt to tell a lost fight from an abandoned
one or from walking past a boss, and no link between records (recording rule 4).

Consequences of the rules:

- Walking past a boss so that its bar shows briefly writes nothing, as long as no damage was dealt.
- Dealing even a little damage and leaving writes an `incomplete` record.
- Opening the map or a menu over the bar for less than the wait window does not split the record.
  Longer than that, the record ends as `incomplete` and a new one starts when the bar is back.
- A multi-phase boss is one record if its bar returns inside the wait window, otherwise two.
- Several bars at once: not covered by the rules yet (open decision 5).

### Records

- One CSV file, `records.csv`, in a folder the user can choose (default: Documents). One row per
  fight with the fields listed under Recording rules, appended when the fight ends.
- Saved as UTF-8 with a byte order mark, so Excel shows Chinese boss names correctly on a
  Chinese-locale Windows.
- Excel locks a file while it is open. If the append fails, the row is held in a small pending
  file next to it and written on the next successful save, so no fight is lost.
- Durations are written twice: as `mm:ss.s` for reading and as seconds for sorting and charts.
- A real `.xlsx` export is a later option. CSV is the store because it needs no extra library,
  appends safely, and diffs cleanly.
- No database, and no HP timeline in the first release.

### Tables

- A user-editable list of named tables. `Arena` and `Normal` are built in, and one table is active.
- The active table is switched from the tray menu or by hotkey and is always shown on the overlay.
- The table name is stamped on the record when the fight starts, as a column in the one CSV file.
- Switching is manual. Detecting the Boss Arena mod automatically is open decision 6.

### User interface

Designed in [UI.md](UI.md): tray menu, overlay, main window (Records, Tables, Hotkeys, Regions,
Settings, About), region calibration, and first-run setup.

- Overlay: small transparent, click-through, topmost window with the active table, boss name,
  running timer and best time. Excluded from capture and kept off the calibrated regions.
- Hotkeys: global system hotkeys, user-configurable per action, with conflict checks.
- The tool must work with the overlay off (tray only), since the record is the product.

### Stack

Python with uv, NumPy, ONNX Runtime, rapidfuzz, PySide6 for the HUD and tray.
Reasons: same proven stack as the example app, fastest to iterate on detection logic, and the hot
path is a tiny NumPy operation a few times per second. If M1 shows Python cannot meet the budget,
the capture and detector loop moves to a small native helper and the rest stays.

Project setup follows the notes for this PC: `PYTHONUTF8=1`, and the package index pinned to
pypi.org in `pyproject.toml`.

## Milestones

### M0 Ground truth

- Record clips at the PC's native resolution in all three languages using the Boss Arena mod:
  full wins, a death, a multi-phase Nightlord, a multi-bar fight, opening the map mid-fight.
- Dump the boss name tables for `engus`, `zhocn`, `zhotw` from the game files and build
  `data/lexicon.csv` (id, en, zh_CN, zh_TW).
- Confirm the defeat text colour check on more kills, including a Nightlord.
- Note where the bar, the name line and the defeat text sit, to write the calibration instructions.

Done when: clips, lexicon and regions are in the repo (clips via Git LFS or kept outside the repo).

### M1 Capture benchmark

- Implement the capture interface and the candidate backends.
- Measure per backend: time per ROI grab, CPU, and game FPS with the tool on vs off at 2 and 10 Hz.
- Check the WGC border on this OS build.

Done when: a default backend is chosen from measured numbers and the budget table has real values.

Status, 2026-11-17: the GDI backend is written (`capture.py`) with a benchmark script
(`tools/bench_capture.py`). Measured on the desktop of the development PC (2560x1440, 12 logical
cores), **without the game running**:

| Mode | Time per sample | CPU used by the process |
|---|---|---|
| Fight: bar region, 10 per second | 4.6 ms grab, 1.4 ms detect | 2.2% of one core (0.18% of the whole CPU) |
| Just after the bar disappears: bar and defeat text, 10 per second | 10.7 ms grab, 2.5 ms detect | 3.8% of one core (0.31%) |
| Idle: bar region, 2 per second | 6.1 ms grab, 1.3 ms detect | too small to measure |

Most of a grab is waiting on Windows, not computing, which is why the CPU share is far below what
the times suggest. Still to do: the same run with the game open, the game's frame rate with the
tool on and off, and a comparison against the other backends if these numbers do not hold.

### M2 Bar detector and HP ratio

- Offline detector working on the M0 clips, with tests that replay frames.
- Tune thresholds, test with HDR off, decide whether HDR needs handling.

Done when: bar presence is correct on every labelled frame of the M0 clips and HP ratio is within
2% of hand-measured values.

### M3 State machine and timer

- Implement states, debounce, backdating, start and end HP %.
- Replay tests assert start, end, status and both HP values per clip.

Done when: every M0 clip gives the right status and a duration within 0.2 s of manual review.

### M4 OCR and lexicon

- Benchmark PP-OCRv5 recognition against Windows.Media.Ocr on name crops from the clips:
  accuracy after lexicon matching, and milliseconds per call.
- Wire the chosen engine in, on demand only.

Done when: every boss in the clips is identified correctly in all three languages.

### M5 Live run, records, HUD

- First-run setup and region calibration, with live preview.
- Live loop against the running game, CSV record store, tray icon, overlay.
- Main window pages from UI.md: Records, Tables, Hotkeys, Regions, Settings, About.
- Keyboard hotkeys. Controller bindings follow in a later release.
- Re-measure the performance budget in a real session.

Done when: a play session produces correct records with no manual input and the budget holds.

### M6 Packaging

- PyInstaller build, settings in the user data folder, diagnostics export, README with the
  safety statement.

## Open decisions

1. **Scope of bosses**: Nightlords only, or every enemy that shows a boss bar. The plan assumes all.
2. **What counts as complete**: settled. The defeat text is the signal, and anything else is
   `incomplete` (recording rules 2 and 7). Bosses that show no defeat text, if any exist, would
   always be recorded `incomplete`.
3. **Licence**: MIT, chosen as the default for the open-source release. The example app is
   AGPL-3.0, so no code or assets may be copied from it. Change the licence before the first
   public release if a different one is wanted.
4. **Online use**: screen reading is the same method the example app uses online, but no vendor
   guarantees it. Offline and Boss Arena use is the tested path first.

5. **Several bars at once**: one record per bar, or one record for the encounter. Not decided.

6. **Choosing the table automatically**: for example from how the game was launched. Manual
   switch until there is a reliable signal that needs no access to the game process.

7. **When the fight ends**: settled. The timer stops when HP reaches zero (recording rule 8).
8. **Reading the defeat text**: settled. It is the same in every language, so it is detected by
   colour and never read as text.
9. **Pass-by records**: settled. Records where the boss HP never changed are skipped (recording
   rule 9).

10. **Nightlord defeat text**: it may differ from the text for other bosses. The project owner
    will check. Development is based on the general-boss clip for now, so until this is checked a
    Nightlord kill may be recorded as `incomplete`.

## Risks

| Risk | Mitigation |
|---|---|
| Colour thresholds break under HDR or unusual display settings | test in M2, document "HDR off" if needed |
| Phase transitions and menus split one fight into several records | accepted under the recording rules for now, revisit after M0 footage |
| OCR misreads stylised Chinese names | closed lexicon, vote over several frames, save unknown crops |
| Game patch moves the HUD or adds bosses | regions and lexicon are data files, not code |
| Capture backend costs FPS on some setups | backend is switchable, benchmark decides the default |
