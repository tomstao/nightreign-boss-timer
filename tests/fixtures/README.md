# Test fixtures

## bar_regions.npz

Twelve small pixel regions cut from one 1920x1080 clip of a complete boss fight. Each is the boss
bar box grown by twice its height above and below: 35 rows by 990 columns, RGB.

| Name | Clip time | What it shows |
|---|---|---|
| no_bar_dark | 5.0 s | no bar, dark scene |
| no_bar_before | 10.9 s | no bar, just before it appears |
| full | 12.0 s | full bar |
| popup_near_full | 19.0 s | a skill popup covers the left end of a nearly full bar |
| half | 38.5 s | about 56% |
| popup_third | 56.8 s | the same popup at about 37% |
| low | 60.5 s | about 14% |
| very_low | 65.0 s | about 5.5% |
| effect_at_one_percent | 71.47 s | about 1%, with a red effect crossing the bar |
| zero | 72.5 s | empty bar still on screen after the kill |
| zero_dissolving | 76.5 s | empty bar while the boss dissolves |
| defeat_text | 78.5 s | bar gone, defeat text on screen |

The expected values in the tests were read from the clip by eye and by an independent scan
(docs/observations.md). The clip itself is not in the repository.

## defeat_regions.npz

Six regions from the same clip, covering the box where the defeat text appears (about 24% to 76%
of the width, 45.5% to 52.5% of the height). Every second pixel is kept, so each is 38 rows by
499 columns, RGB.

| Name | Clip time | What it shows |
|---|---|---|
| fight_start | 12.0 s | fight under way, nothing gold |
| hit_sparks | 55.14 s | hit sparks in the middle of the screen, more gold than the text has |
| sparks_long | 62.0 s | scattered sparks |
| boss_dissolving | 76.5 s | after the kill, before the text |
| text_fading_in | 77.95 s | defeat text fading in |
| text_full | 78.5 s | defeat text fully visible |

## hippo_readings.csv

What the two detectors read from the same clip, sampled 10 times per second: 796 rows of time,
bar present, `hp`, `hp_high`, and defeat text visible. It lets the fight tracker be tested against
a whole real fight without the video.

## tree_sentinel_readings.csv

The same kind of file from a second clip: a 160 s kill of 大树守卫 at 1920x1080, 1,596 rows. This
fight has bright hit flashes that hide the bar for up to 0.6 s (34 gaps) and at the same moment
fill the middle of the screen with gold, which the defeat text check takes for the text on 20
single samples. The clip ends 0.2 s after the real defeat text starts to appear.

## name_regions.npz

Four strips holding the boss name, cut from just above the left end of the bar.

| Name | Source | Text |
|---|---|---|
| clip_1080p_bar_appears | the clip, 11.2 s | 黄金河马 |
| clip_1080p_mid_fight | the clip, 56.8 s, skill popup next to the name | 黄金河马 |
| screenshot_1440p | a 2560x1440 screenshot | 神谕众使者 |
| screenshot_1440p_partly_hidden | a 2560x1440 screenshot, player character in front of the name | 卡利亚禁卫骑士 |

All four are Simplified Chinese. English and Traditional Chinese are not covered yet.

## bar_flash_regions.npz

Four bar regions from the second clip (大树守卫), the same size as those in `bar_regions.npz`.

| Name | Clip time | What it shows |
|---|---|---|
| before_flash | 58.0 s | normal frame, about 55% |
| flash_bright | 59.2 s | hit flash: bright orange behind the bar, which tints the empty track |
| flash_red_scene | 59.5 s | the flash fading: the scene around the bar is red-orange |
| flash_low_hp | 108.4 s | another flash, about 31% |

## bar_popup_regions.npz

Two bar regions from a third clip (卡利亚禁卫骑士, 1920x1080), the same size as those in
`bar_regions.npz`. The boss is at 18% in both, read by eye from the frame before the popup.

| Name | Clip time | What it shows |
|---|---|---|
| before_popup | 135.4 s | normal frame, about 18% |
| popup_over_low_fill | 136.0 s | the skill popup's dark box covers the whole fill, which shows through as dim red |

## bell_bearing_hunter_readings.csv

Detector readings from a fourth clip, like `hippo_readings.csv`: a 75 s kill of a night boss
(铃珠猎人) at 1920x1080, 751 rows, one every 0.1 s. The banner after this kill is the silver
NIGHT REPULSED, so the defeat column is 0 through the kill. The bar empties at 61.4 s and goes
away at 64.5 s. Made with the detector that reads through a skill popup.

## level_regions.npz

Seven crops of the box that holds the player's level, in the emblem at the top left. Six are
from 1920x1080 clips and are 43 rows by 54 columns. One is from a 2560x1440 clip, 57 by 72.

| Name | What it shows |
|---|---|
| level_2 | level 2 |
| level_7 | level 7 |
| level_7_bright_scene | level 7 over a pale floor |
| level_8 | level 8 |
| level_15 | level 15 |
| level_15_at_1440p | level 15, cut from a 2560x1440 frame |
| no_emblem | the same box 2 s into a clip, before the emblem and the level are drawn |

The levels were read by eye. No footage shows levels 1, 3 to 6 or 9 to 14.
