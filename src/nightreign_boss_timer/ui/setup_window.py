"""First-run setup: three short steps shown once, each of which can be skipped.

1. Welcome: what the tool does, the safety statement, the UI language.
2. Game and regions: is the game found, and calibration of the two regions.
3. Basics: the active table, the records folder, the hotkeys.

Nothing here is new: every choice is made through the controller, the same way the main window
makes it, and can be changed there later.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nightreign_boss_timer.i18n import LANGUAGES
from nightreign_boss_timer.settings import DEFAULT_HOTKEYS
from nightreign_boss_timer.tracker import FULL_HP
from nightreign_boss_timer.ui.controller import Controller

STEPS = 3
_GOOD = "color: #2e9e4f; font-weight: bold;"
_BAD = "color: #c8811a; font-weight: bold;"


def _ask_for_folder(parent: QWidget, start: str) -> str:
    return QFileDialog.getExistingDirectory(parent, "", start)


def _text() -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    return label


class SetupWindow(QWidget):
    def __init__(
        self,
        controller: Controller,
        choose_folder: Callable[[QWidget, str], str] = _ask_for_folder,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._choose_folder = choose_folder
        self.resize(640, 440)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size: 15pt; font-weight: bold;")
        self.stack = QStackedWidget()

        # Step 1: welcome.
        self.welcome = _text()
        self.safety = _text()
        self.language_label = QLabel()
        self.language = QComboBox()
        for language in LANGUAGES:
            self.language.addItem(controller.translate(f"language.{language}"), language)
        self.language.activated.connect(
            lambda _index: controller.set_language(self.language.currentData())
        )
        language_row = QHBoxLayout()
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language, 1)
        first = QWidget()
        layout = QVBoxLayout(first)
        layout.addWidget(self.welcome)
        layout.addWidget(self.safety)
        layout.addLayout(language_row)
        layout.addStretch(1)

        # Step 2: game and regions.
        self.game_help = _text()
        self.game_status = QLabel()
        self.bar_status = QLabel()
        self.check_button = QPushButton()
        self.check_button.clicked.connect(self.check_game)
        self.regions_text = _text()
        self.calibrate_button = QPushButton()
        self.calibrate_button.clicked.connect(lambda: controller.calibrate())
        status_row = QHBoxLayout()
        status_row.addWidget(self.game_status)
        status_row.addWidget(self.bar_status, 1)
        status_row.addWidget(self.check_button)
        second = QWidget()
        layout = QVBoxLayout(second)
        layout.addWidget(self.game_help)
        layout.addLayout(status_row)
        layout.addSpacing(12)
        layout.addWidget(self.regions_text)
        layout.addWidget(self.calibrate_button)
        layout.addStretch(1)

        # Step 3: basics.
        self.table_label = QLabel()
        self.table = QComboBox()
        self.table.activated.connect(lambda _index: controller.set_table(self.table.currentText()))
        self.folder_label = QLabel()
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.browse = QPushButton()
        self.browse.clicked.connect(self._browse)
        self.hotkeys = _text()
        self.hotkeys_button = QPushButton()
        self.hotkeys_button.clicked.connect(lambda: controller.show_window("hotkeys"))
        self.later = _text()
        self.later.setStyleSheet("color: gray;")
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.browse)
        third = QWidget()
        layout = QVBoxLayout(third)
        layout.addWidget(self.table_label)
        layout.addWidget(self.table)
        layout.addWidget(self.folder_label)
        layout.addLayout(folder_row)
        layout.addSpacing(12)
        layout.addWidget(self.hotkeys)
        layout.addWidget(self.hotkeys_button)
        layout.addWidget(self.later)
        layout.addStretch(1)

        for page in (first, second, third):
            self.stack.addWidget(page)

        self.skip_button = QPushButton()
        self.back_button = QPushButton()
        self.next_button = QPushButton()
        self.next_button.setDefault(True)
        self.skip_button.clicked.connect(self.finish)
        self.back_button.clicked.connect(lambda: self.go_to(self.stack.currentIndex() - 1))
        self.next_button.clicked.connect(self._next)
        buttons = QHBoxLayout()
        buttons.addWidget(self.skip_button)
        buttons.addStretch(1)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.heading)
        layout.addWidget(self.stack, 1)
        layout.addLayout(buttons)

        controller.changed.connect(self.refresh)
        self.refresh()

    # --- moving between steps -------------------------------------------------------------------

    def start(self) -> None:
        """Open at the first step."""
        self.go_to(0)
        self.show()
        self.raise_()
        self.activateWindow()

    def go_to(self, step: int) -> None:
        self.stack.setCurrentIndex(max(0, min(step, STEPS - 1)))
        if self.stack.currentIndex() == 1:
            self.check_game()
        self.refresh()

    def _next(self) -> None:
        if self.stack.currentIndex() == STEPS - 1:
            self.finish()
        else:
            self.go_to(self.stack.currentIndex() + 1)

    def finish(self) -> None:
        """Close for good, whether by Finish or by Skip setup. It is not shown again by itself."""
        self._controller.finish_setup()
        self.close()

    # --- what the steps do ----------------------------------------------------------------------

    def check_game(self) -> None:
        """Look for the game window now and say what was found."""
        controller, translate = self._controller, self._controller.translate
        probe = controller.probe() if controller.probe else None
        found = probe is not None
        self.game_status.setText(
            translate("statusbar.game_found" if found else "statusbar.game_not_found")
        )
        self.game_status.setStyleSheet(_GOOD if found else _BAD)
        if probe is not None and probe.bar.present:
            percent = 100 if probe.bar.hp >= FULL_HP else round(probe.bar.hp * 100)
            self.bar_status.setText(translate("regions.bar_found", percent=percent))
        else:
            self.bar_status.setText("")

    def _browse(self) -> None:
        folder = self._choose_folder(self, str(self._controller.store.path.parent))
        if folder:
            self._controller.set_records_folder(folder)

    def refresh(self) -> None:
        """Redraw every text from the settings, in the current language."""
        controller, translate = self._controller, self._controller.translate
        settings = controller.settings
        step = self.stack.currentIndex()
        self.setWindowTitle(translate("setup.title"))
        title = translate(("setup.welcome_title", "setup.game_title", "setup.basics_title")[step])
        self.heading.setText(translate("setup.step", step=step + 1, total=STEPS, title=title))

        self.welcome.setText(translate("setup.welcome_text"))
        self.safety.setText(translate("about.safety"))
        self.language_label.setText(translate("settings.language"))
        self.language.setCurrentIndex(self.language.findData(settings.ui_language))

        self.game_help.setText(translate("setup.game_help"))
        self.check_button.setText(translate("setup.check_again"))
        self.regions_text.setText(
            translate("setup.regions_done" if controller.calibrated else "setup.regions_text")
        )
        self.calibrate_button.setText(translate("tray.calibrate"))
        if step == 1:
            self.check_game()

        self.table_label.setText(translate("setup.table_label"))
        self.table.clear()
        self.table.addItems(settings.table_names())
        self.table.setCurrentText(settings.active_table)
        self.folder_label.setText(translate("settings.records_folder"))
        self.folder.setText(str(controller.store.path.parent))
        self.browse.setText(translate("settings.browse"))
        lines = [
            f"{controller.hotkey_of(action)}    {controller.action_label(action)}"
            for action in DEFAULT_HOTKEYS
            if controller.hotkey_of(action)
        ]
        self.hotkeys.setText(translate("setup.hotkeys_text") + "\n" + "\n".join(lines))
        self.hotkeys_button.setText(translate("setup.change_hotkeys"))
        self.later.setText(translate("setup.later"))

        self.skip_button.setText(translate("setup.skip"))
        self.back_button.setText(translate("setup.back"))
        self.back_button.setEnabled(step > 0)
        last = step == STEPS - 1
        self.next_button.setText(translate("setup.finish" if last else "button.next"))
