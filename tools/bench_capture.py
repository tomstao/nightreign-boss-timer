"""Measure what watching the boss bar costs on this PC.

Run it with the game open in borderless or windowed mode, ideally during a boss fight:

    uv run python tools/bench_capture.py

It grabs the boss bar region and runs the detector on it, at the rate used during a fight, and
reports the time per sample and the CPU time the process really used. Add --with-defeat to also
grab and check the defeat text region, which the tool only does for a few seconds after the bar
disappears.
"""

from __future__ import annotations

import argparse
import os
import time

from nightreign_boss_timer.capture import Region, ScreenGrabber, enable_dpi_awareness, find_window
from nightreign_boss_timer.defeat_text import measure_defeat_text
from nightreign_boss_timer.detector import grow_box, measure_bar

# Default regions as fractions of the game image, from docs/observations.md.
BAR = (0.2406, 0.7559, 0.7931, 0.7993)  # left, right, top, bottom
DEFEAT = (0.24, 0.76, 0.455, 0.525)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--title", default="ELDEN RING NIGHTREIGN", help="game window title")
    parser.add_argument("--rate", type=float, default=10.0, help="samples per second")
    parser.add_argument("--seconds", type=float, default=10.0, help="how long to run")
    parser.add_argument("--with-defeat", action="store_true", help="also check the defeat text")
    args = parser.parse_args()

    enable_dpi_awareness()
    window = find_window(args.title)
    if window is None:
        print(f'No window titled "{args.title}". Measuring on the primary screen instead.')
        window = Region(0, 0, _screen_size(0), _screen_size(1))
    print(f"area: {window.width}x{window.height} at ({window.left}, {window.top})")

    bar_top, bar_bottom = grow_box(round(BAR[2] * window.height), round(BAR[3] * window.height))
    bar = Region(
        window.left + round(BAR[0] * window.width),
        window.top + bar_top,
        round((BAR[1] - BAR[0]) * window.width),
        bar_bottom - bar_top + 1,
    )
    defeat = Region(
        window.left + round(DEFEAT[0] * window.width),
        window.top + round(DEFEAT[2] * window.height),
        round((DEFEAT[1] - DEFEAT[0]) * window.width),
        round((DEFEAT[3] - DEFEAT[2]) * window.height),
    )

    grab_ms: list[float] = []
    detect_ms: list[float] = []
    reading = None
    with (
        ScreenGrabber(bar.width, bar.height) as bar_grabber,
        ScreenGrabber(defeat.width, defeat.height) as defeat_grabber,
    ):
        interval = 1.0 / args.rate
        cpu_start = time.process_time()
        end = time.perf_counter() + args.seconds
        while time.perf_counter() < end:
            start = time.perf_counter()
            bar_pixels = bar_grabber.grab(bar.left, bar.top)
            if args.with_defeat:
                defeat_pixels = defeat_grabber.grab(defeat.left, defeat.top)
            grabbed = time.perf_counter()
            reading = measure_bar(bar_pixels)
            if args.with_defeat:
                measure_defeat_text(defeat_pixels)
            done = time.perf_counter()
            grab_ms.append((grabbed - start) * 1000)
            detect_ms.append((done - grabbed) * 1000)
            time.sleep(max(0.0, interval - (done - start)))

        cpu_used = time.process_time() - cpu_start

    samples = len(grab_ms)
    cores = os.cpu_count() or 1
    print(f"samples: {samples} at {args.rate:g} per second")
    print(f"grab:    median {_median(grab_ms):.2f} ms, worst {max(grab_ms):.2f} ms")
    print(f"detect:  median {_median(detect_ms):.2f} ms, worst {max(detect_ms):.2f} ms")
    print(
        f"cpu:     {cpu_used / args.seconds * 100:.2f}% of one core, "
        f"{cpu_used / args.seconds / cores * 100:.2f}% of all {cores}"
    )
    print(f"last bar reading: {reading}")


def _median(values: list[float]) -> float:
    return sorted(values)[len(values) // 2]


def _screen_size(axis: int) -> int:
    import ctypes

    return ctypes.windll.user32.GetSystemMetrics(axis)


if __name__ == "__main__":
    main()
