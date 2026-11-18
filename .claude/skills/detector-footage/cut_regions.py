"""Cut the watched region out of full game frames and save the crops as a test fixture.

    uv run python .claude/skills/detector-footage/cut_regions.py bar out.npz frame1.png frame2.png

Each frame must be a picture of the whole game image. The crops are saved in one ``.npz`` file,
keyed by the frame's file name without its extension. What the detector reads in each crop is
printed. The frames themselves must not be committed; the small crops may be.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from nightreign_boss_timer.defeat_text import measure_defeat_text
from nightreign_boss_timer.detector import measure_bar
from nightreign_boss_timer.regions import (
    DEFAULT_BAR,
    DEFAULT_DEFEAT_TEXT,
    Box,
    Fractions,
    bar_region,
    defeat_text_region,
    name_region,
)


def load_frame(path: Path) -> np.ndarray:
    """A picture file as an RGB array of shape (rows, columns, 3)."""
    image = QImage(str(path)).convertToFormat(QImage.Format.Format_RGB888)
    if image.isNull():
        raise SystemExit(f"Cannot read {path}")
    rows, columns = image.height(), image.width()
    data = np.frombuffer(image.constBits(), np.uint8).reshape(rows, image.bytesPerLine())
    return data[:, : columns * 3].reshape(rows, columns, 3).copy()


def cut(frame: np.ndarray, kind: str, fractions: Fractions | None) -> np.ndarray:
    rows, columns = frame.shape[:2]
    window = Box(0, 0, columns, rows)
    if kind == "bar":
        box = bar_region(window, fractions or DEFAULT_BAR)
    elif kind == "name":
        box = name_region(window, fractions or DEFAULT_BAR)
    else:
        box = defeat_text_region(window, fractions or DEFAULT_DEFEAT_TEXT)
    if box.left < 0 or box.top < 0 or box.left + box.width > columns or box.top + box.height > rows:
        raise SystemExit(f"The {kind} region {box} does not fit in a {columns}x{rows} frame")
    return frame[box.top : box.top + box.height, box.left : box.left + box.width].copy()


def describe(region: np.ndarray, kind: str) -> str:
    if kind == "bar":
        reading = measure_bar(region)
        if not reading.present:
            return "no bar"
        return f"bar, HP {reading.hp:.3f} to {reading.hp_high:.3f}, score {reading.score:.2f}"
    if kind == "defeat_text":
        reading = measure_defeat_text(region)
        return (
            f"{'defeat text' if reading.visible else 'no defeat text'}, gold {reading.gold:.3f}, "
            f"span {reading.span:.2f}, strokes {reading.strokes}"
        )
    return "name strip (read it with ocr.NameReader)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=("bar", "defeat_text", "name"))
    parser.add_argument("output", type=Path, help="the .npz file to write")
    parser.add_argument("frames", type=Path, nargs="+", help="full game frames, as picture files")
    parser.add_argument(
        "--fractions",
        type=float,
        nargs=4,
        metavar=("LEFT", "RIGHT", "TOP", "BOTTOM"),
        help="the region as saved in settings.json (for 'name', the bar's region)",
    )
    args = parser.parse_args()

    fractions = Fractions(*args.fractions) if args.fractions else None
    regions: dict[str, np.ndarray] = {}
    for path in args.frames:
        frame = load_frame(path)
        region = cut(frame, args.kind, fractions)
        regions[path.stem] = region
        size = f"{frame.shape[1]}x{frame.shape[0]}"
        cut_size = f"{region.shape[1]}x{region.shape[0]}"
        print(f"{path.stem}: {size} -> {cut_size}, {describe(region, args.kind)}")
    np.savez_compressed(args.output, **regions)
    print(f"Wrote {len(regions)} regions to {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
