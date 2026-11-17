# Research: terminology and best practice

Collected 2026-11-17. Items marked **(verify)** are not yet confirmed on this machine or in game
and are scheduled for confirmation in the plan.

## 1. Technical terminology

### Overlay

| Term | Meaning |
|---|---|
| External overlay | A separate process that draws its own transparent, always-on-top window over the game. No code runs inside the game. This is what we build. |
| Injected / hooked overlay | A DLL inside the game process that hooks the swap chain `Present` call (Steam overlay, Discord, RTSS). Works in exclusive fullscreen, but is exactly what anti-cheat looks for. Out of scope. |
| Layered window | A Win32 window with `WS_EX_LAYERED`, giving per-pixel alpha so the overlay can be transparent. |
| Click-through | `WS_EX_TRANSPARENT` (plus `WS_EX_NOACTIVATE`) so mouse input passes to the game and the overlay never takes focus. |
| Topmost | `WS_EX_TOPMOST`, keeps the overlay above a borderless game window. |
| Borderless windowed | Game runs as a window the size of the screen and is composited by DWM, so other windows can sit on top. Required for any external overlay. |
| Exclusive fullscreen | Game owns the display output. External overlays are not visible. Unsupported. |
| DWM | Desktop Window Manager, the Windows compositor. |
| Capture exclusion | `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` hides our overlay from screen capture, so our own HUD can never cover the pixels we are analysing. |
| DPI awareness | The process must be per-monitor DPI aware, or window coordinates are scaled and regions drift. |

### Screen capture

| Term | Meaning |
|---|---|
| GDI BitBlt / ScreenDC | Oldest API. Copies pixels on the CPU. Fine for a small region at low rate, works everywhere. |
| PrintWindow | Asks a window to paint itself into a bitmap. Often returns black for DirectX games. |
| DXGI Desktop Duplication (DDA) | Windows 8+ API that hands over the composed monitor image as a GPU texture, with dirty rectangles. Captures a monitor, not a window. No capture border. |
| Windows Graphics Capture (WGC) / FramePool | Windows 10 1803+ API that captures a single window or monitor into a frame pool. Microsoft's recommended API for new apps. Shows a yellow border around the captured target unless `IsBorderRequired = false`, which needs a newer OS build than this PC's Windows 10 19045 **(verify)**. |
| ROI (region of interest) | The small rectangle we actually analyse. Everything else is never copied off the GPU. |
| Normalised region | ROI stored as fractions of the 16:9 game image, so one definition works at 1080p, 1440p and 4K. |
| Calibration | User-drawn override of an ROI when the automatic region is wrong. |
| Detection interval / polling rate | How often a frame is sampled. The example app defaults to 250 ms. |
| Letterbox / pillarbox | Black bars when the window is not 16:9. The game image, not the window, is the coordinate base. |
| HDR tone mapping | HDR output changes captured colours, which breaks colour thresholds. Needs a compensation path or the "disable HDR" advice. |

### Recognition

| Term | Meaning |
|---|---|
| OCR | Optical character recognition, image to text. |
| Text detection vs text recognition | Detection finds where text is, recognition reads a cropped line. With a fixed ROI we skip detection entirely, which removes most of the OCR cost. |
| Template matching | Comparing a region against stored reference images (`cv2.matchTemplate`). Fast, but one template per language and resolution. |
| Colour threshold / mask | Classifying pixels by HSV or RGB range, e.g. "is this pixel boss-bar red". |
| Fill ratio | Bar length as a fraction, found by scanning the bar row for the last filled column. |
| Closed lexicon | The full list of valid strings (boss names). OCR output is snapped to the nearest entry. |
| Fuzzy matching | Edit-distance matching of noisy OCR output to the lexicon (Levenshtein, `rapidfuzz`). |
| Gate / trigger | A cheap check that decides whether an expensive step runs at all. |
| Debounce / hysteresis | Requiring a condition to hold for N samples or T ms before changing state, so one bad frame cannot start or stop the timer. |
| State machine (FSM) | The explicit list of fight states and the transitions between them. |
| Backdating | Recording an event at the timestamp of the first frame that showed it, not the later frame that confirmed it. |
| ONNX Runtime | Portable inference runtime used for the OCR model. The CPU execution provider keeps inference off the GPU the game is using. |

### Timing

| Term | Meaning |
|---|---|
| RTA | Real-time attack, wall-clock time from start to end. This is what we record. |
| IGT | In-game time, which excludes loads and pauses. Needs memory access, so out of scope. |
| Autosplitter | Speedrun tool that starts, splits and stops a timer automatically. Souls autosplitters (SoulSplitter) read process memory. Ours is the vision-based equivalent. |
| Split | A timestamp inside a run, e.g. a phase change. |

## 2. Game terminology (English / 简体 / 繁體)

Only the general term is confirmed so far, taken from the example app's own translation files:

| English | 简体中文 | 繁體中文 | Source |
|---|---|---|---|
| Nightlord | 夜王 | 黑夜王 | example app i18n |

The example app also ships trilingual tables for field bosses (Tree Sentinel / 大树守卫 / 大樹守衛
and about 40 more), but those are shortened community labels, not the strings the game draws on the
boss bar, and the app is AGPL. They are useful for checking, not for copying.

English Nightlord names from memory, to be confirmed against game text **(verify)**:
Gladius, Beast of Night; Adel, Baron of Night; Gnoster, Wisdom of Night; Maris, Fathom of Night;
Libra, Creature of Night; Fulghor, Champion of Nightglow; Caligo, Miasma of Night;
Heolstor the Nightlord; plus the DLC Nightlords and Everdark variants.

Still to collect in all three languages **(verify)**:

- every boss name exactly as drawn above the health bar (Nightlords, night bosses, field bosses, DLC)
- the victory banner (English "NIGHTLORD FELLED" / "GREAT ENEMY FELLED" style text)
- the defeat text shown on a wipe

Best source: dump the game's own name tables (`NpcName` FMG files in the `engus`, `zhocn`, `zhotw`
message bundles) with a community unpacker such as WitchyBND or Smithbox. This reads files on disk,
not the running game, and gives the exact strings and the complete list in one step. Web wikis are
incomplete for Chinese and disagree on wording. Fallback: screenshots from the Boss Arena mod.

## 3. What the example app does

`nightreign-overlay-helper` v1.0.3 (NeuraXmy, AGPL-3.0), inspected from the release folder:

- Python 3.13, PyQt6 + Fluent Widgets UI, OpenCV, NumPy, ONNX Runtime, packaged with PyInstaller.
- One shared **capture engine** feeds every detector. Capture goes through a native DLL
  (`MaaWin32Screencap`, LGPL, from MaaFramework) that speed-tests GDI, WGC FramePool, DXGI
  duplication, PrintWindow and ScreenDC and picks the fastest, with an `mss` fallback.
- One global detection interval, 250 ms by default. Its FAQ names a too-small interval as the
  first cause of stutter.
- Regions are derived automatically from a 16:9 game image, with manual calibration as override.
- **No general OCR engine.** Day icons use per-language templates. The HP marker and map features
  use three small purpose-trained CNNs (0.2 to 1.8 MB ONNX). The user picks the game language.
- Requires windowed or borderless mode. Recommends turning HDR off. Conflicts with frame-generation
  tools such as Lossless Scaling.
- Safety position: screenshots and image analysis only, no memory access, no injection.

Other Nightreign timers found (Nightreign Auto-Timer, a storm phase timer on Nexus) run Tesseract
on keywords such as "DAY". No existing tool was found that reads the boss bar or times fights.

## 4. Best practice

1. **Stay external.** No injection, no memory reads, no game file changes at runtime. This is the
   approach every screen-reading Nightreign tool uses and the reason they are tolerated alongside
   Easy Anti-Cheat. There is no official statement from the anti-cheat vendor, so the README must
   say "use at your own risk" like the example does.
2. **Capture as little as possible, as rarely as possible.** Copy only the ROI. Poll slowly while
   idle and faster only during a fight. The cost that hurts FPS is GPU readback and CPU contention,
   and both scale with pixels times rate.
3. **Put cheap gates before expensive steps.** Colour and shape checks run on every sample. OCR
   runs only when a gate fires, and only a handful of times per fight.
4. **Skip text detection.** The boss name is always in the same place, so run recognition directly
   on the cropped line.
5. **Snap OCR to a closed lexicon.** Stylised game fonts over a moving 3D scene produce noisy text.
   Fuzzy-matching against the known name list makes a mostly-right read exactly right, and the
   lexicon doubles as the language detector.
6. **Keep inference off the GPU.** CPU execution provider, one thread, below-normal process
   priority. A small OCR model on the GPU would compete with the game for the same device.
7. **Debounce and backdate.** Confirm transitions over several samples, then record the timestamp
   of the first sample. This gives stability without adding latency to the recorded time.
8. **Use capture timestamps from a monotonic clock**, not the time at which analysis finished.
9. **Resolution-independent regions** with a manual calibration override.
10. **Exclude the overlay from capture** and keep it away from the ROI.
11. **Record real frames and replay them in tests.** Detection logic is tuned and regression-tested
    against saved clips, not by replaying fights by hand.
12. **Ship a diagnostics export** (recent ROI crops plus log) so wrong detections can be reproduced.

## 5. OCR engine options

| Option | For | Against |
|---|---|---|
| PP-OCRv5 mobile recognition model on ONNX Runtime (RapidOCR packaging) | One model covers Simplified, Traditional and English. Runs recognition-only on CPU. Same runtime the example already ships. | About 15 MB model. Speed on this PC unmeasured **(verify)**. |
| Windows.Media.Ocr | Built in, no model to ship, fast. | Needs the zh-Hans and zh-Hant language packs installed. Quality on stylised fonts unknown. |
| Tesseract | Familiar, used by other Nightreign timers. | Weakest on stylised and CJK text, three language data files, slowest. |
| Per-name templates or a custom CNN | Fastest at runtime, what the example does. | A template set per language and resolution, or a training pipeline. Too much upkeep for 100+ names in three languages. |

Recommendation: PP-OCRv5 mobile recognition plus lexicon matching, with Windows.Media.Ocr as the
comparison in the benchmark milestone.

## Sources

- Example app: the v1.0.3 release folder of nightreign-overlay-helper (README, FAQ, tutorials, i18n, third-party notices)
- https://github.com/NeuraXmy/nightreign-overlay-helper
- https://github.com/hwangeug/nightreign-auto-timer
- https://www.nexusmods.com/eldenringnightreign/mods/196
- https://obsproject.com/forum/threads/windows-graphics-capture-vs-dxgi-desktop-duplication.149320
- https://github.com/Blinue/Magpie/wiki/Comparison-of-capture-methods
- https://github.com/robmikh/Win32CaptureSample/issues/82
- https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html
- https://huggingface.co/monkt/paddleocr-onnx
- https://github.com/FrankvdStam/SoulSplitter
- https://wiki.biligame.com/nightreign/
