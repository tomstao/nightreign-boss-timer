"""The Regions page: whether each region is calibrated, and what the tool reads there right now."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QHideEvent, QPixmap, QShowEvent
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout

from nightreign_boss_timer.regions import Fractions
from nightreign_boss_timer.tracker import FULL_HP
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page
from nightreign_boss_timer.ui.region_canvas import to_image

PREVIEW_MS = 1000
_PREVIEW_WIDTH = 720
_GOOD = "color: #2e9e4f; font-weight: bold;"
_BAD = "color: #c8811a; font-weight: bold;"


def _picture(label: QLabel, image: NDArray[np.uint8], min_height: int) -> None:
    """Show pixels in a label, enlarged to a readable size without smoothing them."""
    pixmap = QPixmap.fromImage(to_image(image))
    height = max(min_height, round(pixmap.height() * _PREVIEW_WIDTH / pixmap.width()))
    label.setPixmap(
        pixmap.scaled(
            _PREVIEW_WIDTH,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    )


class RegionsPage(Page):
    key = "regions"

    def __init__(self, controller: Controller) -> None:
        super().__init__(controller)
        self.bar_name = QLabel()
        self.bar_status = QLabel()
        self.bar_button = QPushButton()
        self.text_name = QLabel()
        self.text_status = QLabel()
        self.text_button = QPushButton()
        self.bar_button.clicked.connect(lambda: controller.calibrate("bar"))
        self.text_button.clicked.connect(lambda: controller.calibrate("defeat_text"))
        self.size = QLabel()

        self.preview_title = QLabel()
        self.preview_title.setStyleSheet("font-weight: bold;")
        self.preview_note = QLabel()
        self.preview_note.setWordWrap(True)
        self.preview_note.setStyleSheet("color: gray;")
        self.bar_picture = QLabel()
        self.bar_readout = QLabel()
        self.text_picture = QLabel()
        self.text_readout = QLabel()
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet(_BAD)

        rows = QGridLayout()
        rows.addWidget(self.bar_name, 0, 0)
        rows.addWidget(self.bar_status, 0, 1)
        rows.addWidget(self.bar_button, 0, 2)
        rows.addWidget(self.text_name, 1, 0)
        rows.addWidget(self.text_status, 1, 1)
        rows.addWidget(self.text_button, 1, 2)
        rows.setColumnStretch(1, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(rows)
        layout.addWidget(self.size)
        layout.addSpacing(12)
        for widget in (
            self.preview_title,
            self.preview_note,
            self.bar_picture,
            self.bar_readout,
            self.text_picture,
            self.text_readout,
            self.warning,
        ):
            layout.addWidget(widget)
        layout.addStretch(1)

        # The screen is only read while this page is on screen.
        self.timer = QTimer(self)
        self.timer.setInterval(PREVIEW_MS)
        self.timer.timeout.connect(self.update_preview)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.update_preview()
        self.timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.timer.stop()

    def _row(self, status: QLabel, button: QPushButton, saved: Fractions | None) -> None:
        translate = self.controller.translate
        status.setText(translate("regions.calibrated" if saved else "regions.default_used"))
        status.setStyleSheet(_GOOD if saved else "")
        button.setText(translate("regions.recalibrate" if saved else "regions.calibrate"))

    def refresh(self) -> None:
        translate, settings = self.controller.translate, self.controller.settings
        self.bar_name.setText(translate("regions.bar"))
        self.text_name.setText(translate("regions.defeat_text"))
        self._row(self.bar_status, self.bar_button, settings.bar_region)
        self._row(self.text_status, self.text_button, settings.defeat_text_region)
        if settings.calibrated_size:
            width, height = settings.calibrated_size
            self.size.setText(translate("regions.calibrated_at", width=width, height=height))
        else:
            self.size.setText("")
        self.preview_title.setText(translate("regions.preview"))
        self.preview_note.setText(translate("regions.preview_note"))
        self.update_preview()

    def update_preview(self) -> None:
        """Read both regions from the screen and show the pixels with what was read in them."""
        translate, settings = self.controller.translate, self.controller.settings
        probe = self.controller.probe() if self.controller.probe else None
        found = probe is not None
        for widget in (self.bar_picture, self.bar_readout, self.text_picture, self.text_readout):
            widget.setVisible(found)
        if probe is None:
            self.warning.setText(translate("overlay.game_not_found"))
            return

        _picture(self.bar_picture, probe.bar_image, 30)
        _picture(self.text_picture, probe.text_image, 0)
        if probe.bar.present:
            percent = 100 if probe.bar.hp >= FULL_HP else round(probe.bar.hp * 100)
            parts = [translate("regions.bar_detected"), translate("overlay.hp", percent=percent)]
            if probe.name:
                parts.append(translate("regions.name_read", name=probe.name))
            self.bar_readout.setText("     ".join(parts))
        else:
            self.bar_readout.setText(translate("regions.bar_not_detected"))
        self.bar_readout.setStyleSheet(_GOOD if probe.bar.present else "")
        seen = probe.defeat.visible
        self.text_readout.setText(
            translate("regions.defeat_found" if seen else "regions.defeat_not_found")
        )
        self.text_readout.setStyleSheet(_GOOD if seen else "")

        changed = settings.calibrated_size is not None and probe.window != settings.calibrated_size
        self.warning.setText(
            translate("regions.window_now", width=probe.window[0], height=probe.window[1])
            if changed
            else ""
        )
