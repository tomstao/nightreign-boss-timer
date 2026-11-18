---
name: detector-footage
description: Change boss bar, defeat text or boss name detection in nightreign-boss-timer, or add test pixels cut from new game footage. Use when a detection is wrong or missed, when tuning thresholds in detector.py, defeat_text.py, tracker.py or ocr.py, or when someone supplies a new clip or screenshot.
---

# Detection and footage

Detection is developed against recorded pixels, never by playing the game. Every change to
detection needs a test that fails without it.

## Where things are

| File | Decides |
|---|---|
| `detector.py` | is a boss bar in this strip, and how full is it |
| `defeat_text.py` | is the gold defeat text in this box (by its look, never by reading it) |
| `tracker.py` | when a fight starts and ends, and whether it is complete, from those readings |
| `ocr.py`, `names.py` | the boss name above the bar, voted over several frames |
| `regions.py` | where each region sits in the game image |

`docs/observations.md` records what was measured from footage and why each rule exists. Read the
part about your detector before changing a threshold, and add what you learn to it.

## Rules

- **Footage stays out of the repository.** Clips and full screenshots are never committed. Only
  small crops go in, as arrays under `tests/fixtures/`, described in `tests/fixtures/README.md`.
- **The owner's recording rules win.** `docs/PLAN.md`, "Recording rules". For example: the timer
  stops when HP reaches zero, not when the bar disappears.
- **Keep the loop cheap.** The bar detector runs ten times a second on a strip of pixels with
  plain NumPy. No model, no per-pixel Python loop. A change there needs before and after numbers
  from `uv run python tools/bench_capture.py`.
- **No fixed brightness cut-offs.** Scene brightness varies. Compare channels to each other and
  the bar to its surroundings, as the existing tests do.

## Adding pixels from a new clip or screenshot

1. Get still frames as PNG files. From a clip, with ffmpeg, at a time in seconds:

   ```powershell
   ffmpeg -ss 59.2 -i clip.mp4 -frames:v 1 flash_bright.png
   ```

   Name each file after what it shows. The name becomes the fixture's key.

2. Cut the watched region out of each frame with `cut_regions.py` in this folder. It prints what
   the detector reads in each frame, so you can see the problem before fixing it:

   ```powershell
   uv run python .claude/skills/detector-footage/cut_regions.py bar tests/fixtures/new_bar.npz flash_bright.png flash_low_hp.png
   uv run python .claude/skills/detector-footage/cut_regions.py defeat_text tests/fixtures/new_text.npz text_full.png
   uv run python .claude/skills/detector-footage/cut_regions.py name tests/fixtures/new_names.npz boss_appears.png
   ```

   It uses the measured 16:9 positions. For another layout pass
   `--fractions LEFT RIGHT TOP BOTTOM` with the values calibration saved in `settings.json`.

3. Add a table for the new file to `tests/fixtures/README.md`: source, clip time, what each
   region shows. State the expected value and how you know it (read by eye, counted frames).

4. Write the test first, in `tests/test_detector.py`, `tests/test_defeat_text.py` or
   `tests/test_ocr.py`, loading the regions with `np.load`. See it fail, then change the detector.

5. Run all tests. The older fixtures must still pass: a fix for one clip must not break another.

## Testing a whole fight

`tests/fixtures/*_readings.csv` hold what the detectors read from an entire clip, ten samples a
second. `tests/test_tracker.py` replays them through the tracker and checks the start, the end,
the status and both HP values. After changing a detector, regenerate the readings from the clip
if you have it; if you do not, say in the pull request that the readings files are older than
the detector.

## Reporting what you could not check

Say in the pull request which footage was used: resolution, game language, and whether HDR was
on. Not yet covered by any footage: English and Traditional Chinese boss names, a Nightlord's
defeat text, two bars at once, 4K and ultrawide.
