"""The calibration window: mark the boss health bar, then the defeat text, on a frozen screenshot.

Each step shows the screenshot with a box to drag. Below it, the detector's answer for the box as
it is right now, so a wrong box is seen before it is saved. Saving writes the box into the
settings as fractions of the game image.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from nightreign_boss_timer.calibration import (
    RegionKind,
    Selection,
    read_bar,
    read_defeat_text,
    starting_selection,
    to_fractions,
)
from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.regions import Fractions
from nightreign_boss_timer.settings import Settings
from nightreign_boss_timer.tracker import FULL_HP
from nightreign_boss_timer.ui.region_canvas import RegionCanvas

STEPS = (RegionKind.BAR, RegionKind.DEFEAT_TEXT)
# The window hides itself before a screenshot. This is how long Windows gets to redraw the game.
HIDE_MS = 300
_GOOD = "color: #2e9e4f; font-weight: bold;"
_BAD = "color: #c8811a; font-weight: bold;"


class CalibrationWindow(QWidget):
    def __init__(
        self,
        settings: Settings,
        translate: Translator,
        take_picture: Callable[[], NDArray[np.uint8] | None],
        on_saved: Callable[[], None],
    ) -> None:
        """``take_picture`` returns the game image, or None if the game window is not found.
        ``on_saved`` is called after each region is written into ``settings``."""
        super().__init__()
        self._settings = settings
        self._translate = translate
        self._take_picture = take_picture
        self._on_saved = on_saved
        self._picture: NDArray[np.uint8] | None = None
        self._step = 0

        self.resize(1280, 800)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size: 15pt; font-weight: bold;")
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.canvas = RegionCanvas()
        self.canvas.selection_changed.connect(self._check)
        self.readout = QLabel()
        self.retake_button = QPushButton()
        self.cancel_button = QPushButton()
        self.skip_button = QPushButton()
        self.save_button = QPushButton()
        self.save_button.setDefault(True)
        self.retake_button.clicked.connect(self.retake)
        self.cancel_button.clicked.connect(self.close)
        self.skip_button.clicked.connect(self._next_step)
        self.save_button.clicked.connect(self.save)

        buttons = QHBoxLayout()
        buttons.addWidget(self.retake_button)
        buttons.addWidget(self.readout, 1)
        for button in (self.cancel_button, self.skip_button, self.save_button):
            # Arrow keys belong to the box, so the buttons must not take the keyboard.
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            buttons.addWidget(button)
        self.retake_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QVBoxLayout(self)
        layout.addWidget(self.heading)
        layout.addWidget(self.hint)
        layout.addWidget(self.canvas, 1)
        layout.addLayout(buttons)

    @property
    def kind(self) -> RegionKind:
        return STEPS[self._step]

    # --- opening and screenshots ----------------------------------------------------------------

    def start(self) -> None:
        """Take a screenshot and open at the first step."""
        self._step = 0
        self._picture = None  # so the box left over from last time is not carried in
        self.retake()

    def retake(self) -> None:
        """Get out of the way of the game, then take a new screenshot and come back."""
        self.hide()
        QTimer.singleShot(HIDE_MS, self.load_picture)

    def load_picture(self) -> None:
        """Take the screenshot now and show the window with it."""
        picture = self._take_picture()
        same_size = (
            picture is not None
            and self._picture is not None
            and picture.shape == self._picture.shape
        )
        box = self.canvas.selection if same_size else None
        self._picture = picture
        self._show_step(box)
        self.showMaximized()
        self.raise_()
        self.activateWindow()
        self.canvas.setFocus()

    # --- steps ----------------------------------------------------------------------------------

    def _saved(self) -> Fractions | None:
        bar = self.kind is RegionKind.BAR
        return self._settings.bar_region if bar else self._settings.defeat_text_region

    def _show_step(self, box: Selection | None = None) -> None:
        """Fill the window for the current step. ``box`` keeps a box already being worked on."""
        translate = self._translate
        # Every text is set here, not when the window is built, so a change of language is
        # picked up the next time the window opens.
        self.setWindowTitle(translate("calibration.title"))
        self.retake_button.setText(translate("calibration.retake"))
        self.cancel_button.setText(translate("button.cancel"))
        self.skip_button.setText(translate("button.skip"))
        bar = self.kind is RegionKind.BAR
        region = translate("regions.bar" if bar else "regions.defeat_text")
        self.heading.setText(
            translate("calibration.step", step=self._step + 1, total=len(STEPS), region=region)
        )
        hint = translate("regions.bar_hint" if bar else "regions.defeat_hint")
        if not bar:
            hint += " " + translate("calibration.defeat_note")
        self.hint.setText(hint + "\n" + translate("calibration.keys_hint"))
        last = self._step == len(STEPS) - 1
        self.save_button.setText(translate("button.save" if last else "calibration.save_next"))
        self.skip_button.setVisible(not last)
        self.save_button.setEnabled(self._picture is not None)
        if self._picture is None:
            self.canvas.setVisible(False)
            self.readout.setStyleSheet(_BAD)
            self.readout.setText(translate("calibration.no_game"))
            return
        self.canvas.setVisible(True)
        rows, columns = self._picture.shape[:2]
        self.canvas.set_picture(
            self._picture, box or starting_selection(self._saved(), self.kind, columns, rows)
        )
        self._check()

    def _fractions(self) -> Fractions:
        rows, columns = self._picture.shape[:2]
        return to_fractions(self.canvas.selection, self.kind, columns, rows)

    def _check(self) -> None:
        """Run the detector on the box as it is now and say what it sees."""
        if self._picture is None:
            return
        translate = self._translate
        if self.kind is RegionKind.BAR:
            reading = read_bar(self._picture, self._fractions())
            found = reading.present
            # A full bar reads a little under 100, because its right tip fades out. Records
            # write such a bar as 100, so the check does too.
            percent = 100 if reading.hp >= FULL_HP else round(reading.hp * 100)
            text = translate(
                "regions.bar_found" if found else "regions.bar_not_found", percent=percent
            )
        else:
            found = read_defeat_text(self._picture, self._fractions()).visible
            text = translate("regions.defeat_found" if found else "regions.defeat_not_found")
        self.readout.setStyleSheet(_GOOD if found else _BAD)
        self.readout.setText(text)

    def save(self) -> None:
        """Write the box into the settings and move on."""
        if self._picture is None:
            return
        rows, columns = self._picture.shape[:2]
        if self.kind is RegionKind.BAR:
            self._settings.bar_region = self._fractions()
        else:
            self._settings.defeat_text_region = self._fractions()
        self._settings.calibrated_size = (columns, rows)
        self._on_saved()
        self._next_step()

    def _next_step(self) -> None:
        if self._step == len(STEPS) - 1:
            self.close()
            return
        self._step += 1
        self._show_step()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.save()
        else:
            super().keyPressEvent(event)
