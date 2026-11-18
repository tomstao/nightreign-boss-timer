# Observations from game screenshots

Measured 2026-11-17 from two screenshots and one video clip supplied by the project owner, all
with the game in Simplified Chinese. This is the first ground truth for milestone M0. The numbers
are starting values, not final thresholds.

## Screenshots

Both screenshots are 2560x1440.

| Screenshot | Scene | Boss name shown | Bar state |
|---|---|---|---|
| A | open field, normal game | 神谕众使者 | full |
| B | arena, mid-fight | partly hidden behind the player character | partly depleted |

## Boss bar geometry

The bar is in the same place in both screenshots.

| | Pixels at 2560x1440 | Fraction of the screen |
|---|---|---|
| Left edge | x = 616 | 0.2406 |
| Right edge | x = 1935 | 0.7559 |
| Width | 1320 | 0.5156 |
| Top of fill | y = 1142 | 0.7931 |
| Bottom of fill | y = 1151 | 0.7993 |
| Fill height | about 10, about 14 including the soft edges | under 1% of screen height |

- The bar is thin. At 1080p the fill is only about 7 pixels tall, so the detector should average
  over the rows of the fill instead of reading a single row.
- A bright highlight line runs along the bottom edge of the bar (about RGB 220, 186, 175).

## Boss name

- The name sits directly above the left end of the bar, left-aligned with it (it starts 2 px to
  the right of the bar's left edge).
- In screenshot A the text occupies y = 1096 to 1124: its top is 46 px above the bar and its
  bottom 18 px above, so the line is about 28 px tall at 1440p.
- The text is near-white with a dark outline, drawn over the moving scene with no background panel.
- Deriving the name region from the calibrated bar looks workable: same left edge, from about
  5 bar-heights above the bar to about 1.5 above, and wide enough for the longest name.
- In screenshot B the player character stands in front of part of the name. The name must be read
  over several frames and voted on, as planned. One frame is not reliable.

## Colours

| Part | Screenshot A | Screenshot B |
|---|---|---|
| Filled bar | about (110, 53, 24) | about (95, 39, 15) |
| Empty bar | not visible (bar full) | about (45, 43, 40), dark neutral grey |
| Just-lost section | not visible | about (226, 217, 206), near white |

- The fill is a dark brownish red, and its brightness differs between scenes. A fixed brightness
  cut-off fails: `red > 110` missed half of a full bar in A, and `red > 90` broke up the bar in B.
- A ratio test holds in both: red at least 1.5 times green and 1.9 times blue, with a low
  brightness floor (red above about 60). With it, 98.9% of the columns of the full bar in A read as
  filled, the remainder being the faded right tip.
- The section that was just lost is near white for a moment, then turns to the dark empty colour.
  HP % should count only the red part.
- A damage number appears above the right end of the bar after a hit (screenshot B shows 1009).
  It is outside the fill rows and outside the name region.

## Things that can fool the detector

- Screenshot B has red in the scene right next to the bar: the boss's body and a blood effect
  near the bar's right end. Colour alone is not enough for "bar present". The check should also
  require the bar's shape: a long, thin, horizontal run that starts exactly at the left edge.
- The player character and effects can cover the name and can cross the bar itself.
- Screenshot A has motion blur behind the bar. The bar stays sharp, because the HUD is drawn on top.

## Clip of a complete fight

Analysed 2026-11-17: one clip supplied by the project owner, 1920x1080 at 60 fps, 79.7 s long,
arena, game language Simplified Chinese, boss 黄金河马. The boss is killed.

### Timeline

| Clip time | What happens |
|---|---|
| 0.0 to 11.1 s | no bar |
| 11.13 s | bar appears, full, from one frame to the next (no fade-in) |
| 11.1 to 71.6 s | HP falls from 99% to 1% |
| 71.61 s | HP reaches zero |
| 71.6 to 77.5 s | the empty bar and the name stay on screen while the boss dissolves |
| about 77.6 s | bar and name disappear |
| 77.9 s | defeat text starts to appear, fully visible from 78.0 s |
| 79.7 s | clip ends with the defeat text still on screen |

- Bar appears to HP zero: **60.5 s**. Bar appears to bar gone: **66.4 s**.
- The two differ by about 6 s of death animation. The project owner chose the first: the timer
  stops when HP reaches zero (PLAN.md, recording rule 8).

### What the clip confirms

- The bar fractions measured at 1440p landed exactly on the bar at 1080p, with no adjustment.
  Manual calibration stays the rule for the first release, but the fractions are a good default
  to pre-fill the selection box with.
- The ratio colour test tracked HP through the whole fight, down to the last 1%.
- The empty bar is a dark strip clearly darker than the rows above and below it (about 22 against
  40 on a 0 to 255 scale in this clip). That makes "bar present" detectable even at zero HP.

### What the clip adds

- **The defeat text is in English in a Chinese-language game.** It reads GREAT ENEMY FELLED, in
  gold, centred, on a dark band across the middle of the screen (about 26% to 74% of the width,
  at about 49% of the height). If this holds for Traditional Chinese too, the defeat text needs no
  per-language handling.
- **The defeat text does not need text recognition, but gold alone is not enough.** The share of
  gold pixels in that band is a steady 10.2 to 10.4% from 78.0 s until the clip ends. An earlier
  version of this note said it was zero for the entire fight. That was wrong: it had only been
  measured around the start and the end. Over the whole fight, hit sparks and weapon effects in
  the middle of the screen put gold in the band during 12 short spans, once reaching more gold
  than the text itself (at 55.1 s).
- **Shape separates the text from the sparks.** The text is many separate letters spread along a
  line, on a dark band: 18 to 24 separate gold strokes spanning over half the box. The sparks are
  a few blobs: at most 8 strokes in the frames with the most gold. With gold share, span, stroke
  count and band darkness together, a scan of the whole clip at 20 samples per second gave no
  false positive and no miss, for both a tight and a loose box. The text holds steady for seconds
  while sparks flicker, so requiring several agreeing samples adds a second safeguard.
- **A HUD popup covers the left end of the bar.** When the player uses a weapon skill, a box with
  the skill name (血刃 in this clip) appears at the left and overlaps the bar's left end for about
  a second. It happened about nine times in this fight. A detector that requires the red to start
  exactly at the left edge loses the bar each time. HP must be read from where the red **ends**,
  not from an unbroken run starting at the left.
- **Effects cross the bar.** For about 0.15 s just before the kill, a red effect in the scene made
  the bar look 25 to 37% full when it was at 1%. HP readings need smoothing, and HP should never
  be allowed to go up within a fight.
- The boss in this clip is red and fills much of the screen. The bar was still tracked correctly,
  because the scene's red was not a long thin horizontal strip.

## Still needed

- English and Traditional Chinese frames of the boss name. The defeat text is the same in every
  language (confirmed by the project owner), so it needs none.
- A lost or abandoned fight is no longer needed: any end without defeat text is `incomplete`.
- How long the defeat text stays on screen (the clip ends first).
- A Nightlord kill, to see whether the defeat text differs from GREAT ENEMY FELLED.
- A fight with two bars at once, and a multi-phase boss.
- A clip at 3840x2160 or an ultrawide resolution, if any player uses one.

## Second clip: hit flashes

Analysed 2026-11-17: 1920x1080, 160 s, arena, Simplified Chinese, boss 大树守卫, killed. The clip
ends 0.2 s after the defeat text starts to appear.

- The boss name was read correctly on all 8 attempts.
- HP was tracked from 99% to 0%. The last hit lands at about 151.5 s.
- **Hit flashes are the main hazard.** A critical hit fills the screen with a bright orange-gold
  burst for up to 0.6 s. During it the bar is still drawn, but the detector loses it (34 gaps in
  this fight, against 7 in the first clip), because the scene around the bar turns red-orange and
  the empty track no longer looks dark.
- **The same flash looks like defeat text.** On 20 single samples the defeat text check answered
  yes, in runs of at most 3 samples. So "bar gone" and "gold text" can be true together in the
  middle of a fight, which is exactly the signal for a kill.
- The tracker now guards against this in two ways: the defeat text must hold for 0.8 s, and it
  only counts if the boss was at 10% HP or less when the bar was last read. Replaying this clip
  gives no early end.
- A gap right as the bar appeared made the start time 0.2 s late. A bar being confirmed may now
  drop out briefly without starting over.
- The bar detector was then changed to hold through most of a flash. Two things were going
  wrong. The empty track is see-through, so over a bright flash it turns brownish and no longer
  passed as "dark and colourless". And when the scene around the bar turned red-orange, the red
  fill was rejected as a red object in the scene. The track is now also accepted when it is much
  darker and less colourful than what is around it, and the fill when it is clearly darker than
  a red scene. Gaps in this clip went from 34 to 16 and the longest from 0.6 s to 0.3 s. In the
  first clip they went from 7 to 5. The remaining gaps are one or two samples long.

## Twenty clips: the skill popup at low HP

Analysed 2026-11-18: 20 clips at 1920x1080, Simplified Chinese, 19 of them kills.

- **A skill popup made the bar read as empty.** The popup box (血刃 in these clips) is a dark
  see-through layer over the left end of the bar, on screen for about 1.0 s. When the boss is
  below about 18%, it covers all of the fill. The fill then shows as dim red, about (49, 26, 30),
  which failed the fill colour test and passed for empty track. This gave 42 runs of wrong empty
  readings in the middle of 12 of the clips, 27 of them 0.4 to 1.1 s long.
- The fill under the popup is still much redder than the scene beside it (red to green about 1.9
  against 0.95). The empty track is see-through and only ever as red as the scene. The detector
  now counts a column as fill on that comparison. The runs are gone. What is left is single wrong
  empty samples: five clips have one, as the bar fades in or in mid-fight.
- The same change reads the last sliver of fill slightly better: a boss at 0.6% was read as empty
  0.8 s before its bar really emptied.
- `hippo_readings.csv` and `tree_sentinel_readings.csv` were made before this change and were
  not regenerated: decoding the clips again did not give the same pixels as the first time, so
  a new file would mix that difference with the detector's.

## Kills without the gold text

Analysed 2026-11-18, from the same 20 clips.

- **A night boss shows a different banner.** After the kill of 铃珠猎人 the banner reads NIGHT
  REPULSED in silver-white letters on a faint band, in the same place as the gold text, from
  about 0.3 s to 3 s after the bar goes away. The gold check does not see it, so the kill was
  saved as `incomplete`. The project owner adds that bosses with two stages do not always show
  a banner at all.
- **The empty bar is the dependable sign.** In all 19 kill clips the bar read empty for 1.7 s or
  more before it went away. The tracker now calls that a kill when the wait window ends
  (PLAN.md, recording rule 11). With it, all 19 clips replay as complete from 100% to 0%.
- **Wrong readings that would spoil this.** The bar fading in read as empty for one sample in
  two clips, which made the record start at 0%. Blood crossing the empty bar after a kill read
  as 7% to 11% for two samples in a row. HP is now the middle of three readings, goes up only
  after a second of higher readings, and the kill time survives four stray readings in a row.
- **A paler strip follows the fill.** After a hit, the HP just lost stays for about 0.7 s as a
  paler strip beyond the red. The detector reports it as an unsure reading, so after the last
  hit the clock stops when the strip has gone: 0.7 s late in the 铃珠猎人 clip.
- Not seen in any clip: a boss whose bar refills for a second stage, and a menu over the bar.

### Banners after a kill

Collected 2026-11-18. Only the first two were seen in footage. The rest come from wikis and
forum posts and have not been checked in the game. Their colours are not known.

| Banner | When | Source | Recognised by the gold check |
|---|---|---|---|
| GREAT ENEMY FELLED (gold) | a boss in the field or the arena | footage | yes |
| NIGHT REPULSED (silver) | the boss at the end of a night | footage | no |
| NIGHTLORD SLAIN, also reported as NIGHTLORD FELLED | a Nightlord | Fandom wiki, GamesRadar | unknown |
| VICTORY ACHIEVED | Centipede Demon | forum post | unknown |
| HEIR OF FIRE DESTROYED | Nameless King | forum post | unknown |

The check goes by how the text looks and never reads it, so a new wording in gold needs no
change. A banner in another colour is covered by the empty bar, as long as the bar is readable
when the boss dies.

## The player's level

Analysed 2026-11-18: 21 clips, one frame every 2 s, 1,228 frames. 20 clips are 1920x1080 and one
is 2560x1440. The levels in them are 2, 7, 8 and 15, read by eye.

- The level is one or two white digits in the middle of a round blue emblem at the top left.
  At 1080p the digits are about 16 pixels high, centred near (104, 54).
- **The text model reads the box badly as it is.** With a fixed box around the digits it gave
  the right level in 43% to 85% of the frames, depending on the box, and the rest were letters,
  Chinese characters or other digits. The bright lines of the emblem are the cause.
- **Limiting the answer to digits helps, but the box edges still matter.** Moving the top or the
  bottom edge by one or two pixels moved the share of wrong readings between none and one in six,
  with no steady pattern. A box that depends on single pixels would not survive another resolution.
- **Finding the digits first makes it steady.** The digits are the only solid white shapes in
  the box: the lines are thin and bluer. Cutting a tight crop around them and reading that gave
  the same result for boxes from 50 by 40 to 58 by 46 pixels. A box 66 by 50 or larger takes in
  bright parts of the emblem and fails, so the default box is 54 by 43, in the middle of the
  range that works.
- Result with the default box: 1,166 frames right, 2 wrong (15 read as 2, both in one clip), and
  60 with no digits found, about 3 per clip, where the emblem is not drawn yet or the screen is
  fading. The 2560x1440 frame reads correctly with the same fractions.
- Not covered: levels 1, 3 to 6 and 9 to 14, other resolutions and ultrawide, and a level that
  changes during a fight.
- Run through the whole engine, six clips gave the right level in their record: 2, 7, 7, 8, 15
  at 1920x1080 and 15 at 2560x1440. The level is read at the start of a fight until three
  readings agree, eight have been made, or 50 looks found no digits.

## Boss names in three languages

Collected 2026-11-18.

- `src/nightreign_boss_timer/boss_names.json` lists 210 names, each in English, Simplified
  Chinese and Traditional Chinese. They are the non-empty entries of the game's own name text
  (`NpcName` and `NpcName_dlc01`, for the base game and The Forsaken Hollows) for the three
  languages, joined by entry number, with player characters and merchants left out. The copy
  used is the one in the MIT-licensed project
  <https://github.com/alfizari/Elden-Ring-Nightreign-Save-Editor> (`src/Resources/Text`), as it
  was on 2026-01-15. No name was translated or converted by hand.
- Checked against other sources: the eight Simplified names read from footage are all in the
  list as written, and Steam's achievement text has the same eight Nightlord names in all three
  languages.
- **Not every entry is a boss with a health bar.** The list is every name the game has for a
  non-player character, so some entries may never appear above a boss bar. That does no harm:
  the list is only used to recognise a name that was read.
- **Punctuation differs by language.** A Nightlord's title is in curly quotes in Simplified
  (“黑夜野兽”格拉狄乌斯) and in corner brackets in Traditional (「黑夜野獸」格拉狄烏斯). The lookup
  ignores punctuation, spaces and case, because the text model often drops them.
- **20 names are written the same in both kinds of Chinese** (王室幽魂, for one). Such a name
  cannot tell which Chinese the game is in.
- **A few names are not one to one.** "Omen" is both 恶兆之子 and 恶兆之子们, and 黑夜猎人 is both
  "Night Hunter" and "Night Huntsman". The lookup then leaves that translation empty.
- Names added to the game after January 2026 are missing. A name that is not in the list is
  recorded as it was read.
