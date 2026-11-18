"""The Settings page. Every change is applied and saved at once: there is no Save button."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nightreign_boss_timer.i18n import LANGUAGES
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page


def _ask_for_folder(parent: QWidget, start: str) -> str:
    return QFileDialog.getExistingDirectory(parent, "", start)


def _note() -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    label.setStyleSheet("color: gray;")
    return label


class SettingsPage(Page):
    key = "settings"

    def __init__(
        self,
        controller: Controller,
        choose_folder: Callable[[QWidget, str], str] = _ask_for_folder,
    ) -> None:
        """``choose_folder`` shows the folder dialog and returns the choice, or nothing."""
        super().__init__(controller)
        self._choose_folder = choose_folder

        self.language = QComboBox()
        for language in LANGUAGES:
            # Each language is listed under its own name, whatever the current language is.
            self.language.addItem(controller.translate(f"language.{language}"), language)
        self.language.activated.connect(
            lambda _index: controller.set_language(self.language.currentData())
        )

        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.browse = QPushButton()
        self.default_folder = QPushButton()
        self.open_folder = QPushButton()
        self.browse.clicked.connect(self._browse)
        self.default_folder.clicked.connect(lambda: controller.set_records_folder(""))
        self.open_folder.clicked.connect(controller.open_records_folder)
        self.folder_note = _note()

        self.wait_window = QDoubleSpinBox()
        self.wait_window.setRange(1.0, 120.0)
        self.wait_window.setDecimals(0)
        self.wait_window.valueChanged.connect(
            lambda value: controller.set_option("wait_window_s", float(value))
        )
        self.wait_note = _note()
        self.skip_walk_pasts = QCheckBox()
        self.skip_walk_pasts.toggled.connect(
            lambda on: controller.set_option("skip_walk_pasts", bool(on))
        )
        self.fight_rate = QDoubleSpinBox()
        self.fight_rate.setRange(1.0, 30.0)
        self.fight_rate.setDecimals(0)
        self.fight_rate.valueChanged.connect(
            lambda value: controller.set_option("fight_rate", float(value))
        )
        self.rate_note = _note()

        self.overlay_group = QGroupBox()
        self.overlay_note = _note()
        self.reset_position = QPushButton()
        self.reset_position.clicked.connect(lambda: controller.set_overlay_position(None))
        self.overlay_in_captures = QCheckBox()
        self.overlay_in_captures.toggled.connect(
            lambda on: controller.set_option("overlay_in_captures", bool(on))
        )
        self.captures_note = _note()
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(self.overlay_note, 1)
        overlay_row.addWidget(self.reset_position)
        overlay_box = QVBoxLayout(self.overlay_group)
        overlay_box.addLayout(overlay_row)
        overlay_box.addWidget(self.overlay_in_captures)
        overlay_box.addWidget(self.captures_note)

        self.general = QGroupBox()
        self.language_label = QLabel()
        self.setup_button = QPushButton()
        self.setup_button.clicked.connect(controller.show_setup)
        general = QFormLayout(self.general)
        general.addRow(self.language_label, self.language)
        general.addRow(self.setup_button)

        self.records = QGroupBox()
        self.folder_label = QLabel()
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        for button in (self.browse, self.default_folder, self.open_folder):
            folder_row.addWidget(button)
        records = QVBoxLayout(self.records)
        records.addWidget(self.folder_label)
        records.addLayout(folder_row)
        records.addWidget(self.folder_note)

        self.detection = QGroupBox()
        self.wait_label = QLabel()
        self.rate_label = QLabel()
        detection = QFormLayout(self.detection)
        detection.addRow(self.wait_label, self.wait_window)
        detection.addRow(self.wait_note)
        detection.addRow(self.skip_walk_pasts)
        detection.addRow(self.rate_label, self.fight_rate)
        detection.addRow(self.rate_note)

        layout = QVBoxLayout(self)
        for group in (self.general, self.records, self.detection, self.overlay_group):
            layout.addWidget(group)
        layout.addStretch(1)

    def _browse(self) -> None:
        folder = self._choose_folder(self, str(self.controller.store.path.parent))
        if folder:
            self.controller.set_records_folder(folder)

    def refresh(self) -> None:
        controller, translate = self.controller, self.controller.translate
        settings = controller.settings
        self.general.setTitle(translate("settings.group.general"))
        self.records.setTitle(translate("settings.group.records"))
        self.detection.setTitle(translate("settings.group.detection"))
        self.language_label.setText(translate("settings.language"))
        self.setup_button.setText(translate("setup.again"))
        self.folder_label.setText(translate("settings.records_folder"))
        self.browse.setText(translate("settings.browse"))
        self.default_folder.setText(translate("settings.default_folder"))
        self.open_folder.setText(translate("records.open_folder"))
        self.folder_note.setText(translate("settings.folder_note"))
        self.wait_label.setText(translate("settings.wait_window"))
        self.wait_note.setText(translate("settings.wait_window_note"))
        self.skip_walk_pasts.setText(translate("settings.skip_walk_pasts"))
        self.rate_label.setText(translate("settings.fight_rate"))
        self.rate_note.setText(translate("settings.fight_rate_note"))
        self.overlay_group.setTitle(translate("settings.group.overlay"))
        self.overlay_note.setText(translate("settings.overlay_note"))
        self.reset_position.setText(translate("settings.reset_position"))
        self.overlay_in_captures.setText(translate("settings.overlay_in_captures"))
        self.captures_note.setText(translate("settings.overlay_in_captures_note"))
        self.reset_position.setEnabled(settings.overlay_position is not None)

        # Show the values without each of them reporting a change back to the controller.
        widgets = (
            self.language,
            self.wait_window,
            self.skip_walk_pasts,
            self.fight_rate,
            self.overlay_in_captures,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.language.setCurrentIndex(self.language.findData(settings.ui_language))
        self.wait_window.setValue(settings.wait_window_s)
        self.skip_walk_pasts.setChecked(settings.skip_walk_pasts)
        self.fight_rate.setValue(settings.fight_rate)
        self.overlay_in_captures.setChecked(settings.overlay_in_captures)
        for widget in widgets:
            widget.blockSignals(False)
        self.folder.setText(str(controller.store.path.parent))
        self.default_folder.setEnabled(bool(settings.records_folder))
