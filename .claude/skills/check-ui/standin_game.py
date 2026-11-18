"""Show a screenshot in a borderless window, as a stand-in for the game window.

    uv run python .claude/skills/check-ui/standin_game.py shot.png --size 1920x1080

Then point the tool at it with ``--title "NBT stand-in"``. Close it with Esc or Alt+F4, or pass
``--seconds 20`` to have it close by itself.
"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from nightreign_boss_timer.capture import enable_dpi_awareness


class StandIn(QLabel):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="a full-frame game screenshot")
    parser.add_argument("--size", default=None, help="window size in pixels, such as 1920x1080")
    parser.add_argument("--title", default="NBT stand-in", help="window title to give it")
    parser.add_argument("--at", default="0,0", help="top-left corner on the desktop, as x,y")
    parser.add_argument("--seconds", type=float, default=0, help="close by itself after this long")
    args = parser.parse_args()

    enable_dpi_awareness()
    application = QApplication(sys.argv[:1])
    picture = QPixmap(args.image)
    if picture.isNull():
        print(f"Cannot read {args.image}")
        return 1
    if args.size:
        width, height = (int(part) for part in args.size.lower().split("x"))
        picture = picture.scaled(
            width,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    window = StandIn()
    window.setWindowTitle(args.title)
    window.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    scale = window.devicePixelRatioF()
    picture.setDevicePixelRatio(scale)
    window.setPixmap(picture)
    # A fixed size, or Qt shrinks a window that is larger than two thirds of the screen.
    window.setFixedSize(round(picture.width() / scale), round(picture.height() / scale))
    x, y = (int(part) for part in args.at.split(","))
    window.move(x, y)
    window.show()
    if args.seconds > 0:
        QTimer.singleShot(round(args.seconds * 1000), application.quit)
    print(f'Showing {picture.width()}x{picture.height()} as "{args.title}". Esc closes it.')
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
