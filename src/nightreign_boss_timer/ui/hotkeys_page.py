"""The Hotkeys page: every action with its shortcut, and a field to press a new one into."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFocusEvent, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from nightreign_boss_timer.hotkeys import KEYS, MODIFIERS, normalise
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page

_WARNING = QColor(200, 129, 26)
_MESSAGE = "color: #c8811a; font-weight: bold;"

_QT_MODIFIERS = {
    "Ctrl": Qt.KeyboardModifier.ControlModifier,
    "Alt": Qt.KeyboardModifier.AltModifier,
    "Shift": Qt.KeyboardModifier.ShiftModifier,
    "Win": Qt.KeyboardModifier.MetaModifier,
}
_QT_KEYS = {
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_PageUp: "PageUp",
    Qt.Key.Key_PageDown: "PageDown",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_Insert: "Insert",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Pause: "Pause",
    Qt.Key.Key_Semicolon: ";",
    Qt.Key.Key_Equal: "=",
    Qt.Key.Key_Comma: ",",
    Qt.Key.Key_Minus: "-",
    Qt.Key.Key_Period: ".",
    Qt.Key.Key_Slash: "/",
    Qt.Key.Key_QuoteLeft: "`",
    Qt.Key.Key_BracketLeft: "[",
    Qt.Key.Key_Backslash: "\\",
    Qt.Key.Key_BracketRight: "]",
    Qt.Key.Key_Apostrophe: "'",
}
_NAME_BY_CODE = {code: name for name, code in KEYS.items()}


def key_name(key: int, modifiers: Qt.KeyboardModifier, native_code: int = 0) -> str:
    """The name of a pressed key as shortcuts spell it, or nothing if it cannot be a hotkey.

    Windows' own code for the key is used when it is known, because with Shift held Qt reports
    the shifted character (``!``) instead of the key (``1``).
    """
    if native_code in _NAME_BY_CODE:
        return _NAME_BY_CODE[native_code]
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
        return f"F{key - Qt.Key.Key_F1 + 1}"
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        digit = chr(key)
        return f"Num{digit}" if modifiers & Qt.KeyboardModifier.KeypadModifier else digit
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(key)
    try:
        return _QT_KEYS.get(Qt.Key(key), "")
    except ValueError:  # a key Qt has no name for
        return ""


class ShortcutEdit(QLineEdit):
    """A field that shows the shortcut pressed into it instead of typed text."""

    # Enter was pressed: use what the field shows.
    accepted = Signal()
    # Backspace was pressed: the action should have no shortcut.
    cleared = Signal()
    # The field got (True) or lost (False) the keyboard.
    focus_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accepted.emit()
        elif key == Qt.Key.Key_Escape:
            self.clear()
        elif key == Qt.Key.Key_Backspace:
            self.cleared.emit()
        else:
            name = key_name(key, event.modifiers(), event.nativeVirtualKey())
            if name:
                held = [m for m in MODIFIERS if event.modifiers() & _QT_MODIFIERS[m]]
                self.setText(normalise("+".join([*held, name])))
        # Nothing is passed on: Tab, Alt and the rest must not leave the field or open a menu.

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.focus_changed.emit(False)


class HotkeysPage(Page):
    key = "hotkeys"

    def __init__(self, controller: Controller) -> None:
        super().__init__(controller)
        self._actions: list[str] = []
        self.table = QTableWidget(0, 2)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.capture.setFocus())

        self.capture = ShortcutEdit()
        self.capture.accepted.connect(self.set_shortcut)
        self.capture.cleared.connect(self.clear_shortcut)
        self.capture.focus_changed.connect(controller.suspend_hotkeys)
        self.set_button = QPushButton()
        self.clear_button = QPushButton()
        self.defaults_button = QPushButton()
        self.set_button.clicked.connect(self.set_shortcut)
        self.clear_button.clicked.connect(self.clear_shortcut)
        self.defaults_button.clicked.connect(self.restore_defaults)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setStyleSheet(_MESSAGE)
        self.help = QLabel()
        self.help.setWordWrap(True)
        self.help.setStyleSheet("color: gray;")

        row = QHBoxLayout()
        row.addWidget(self.capture, 1)
        for button in (self.set_button, self.clear_button, self.defaults_button):
            row.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(row)
        layout.addWidget(self.message)
        layout.addWidget(self.help)

    def selected(self) -> str:
        """The selected action, or nothing."""
        row = self.table.currentRow()
        return self._actions[row] if 0 <= row < len(self._actions) else ""

    def _selection_changed(self) -> None:
        chosen = bool(self.selected())
        self.set_button.setEnabled(chosen)
        self.clear_button.setEnabled(chosen)

    def refresh(self) -> None:
        controller, translate = self.controller, self.controller.translate
        keep = self.selected()
        self._actions = controller.hotkey_actions()
        self.table.setHorizontalHeaderLabels(
            [translate("hotkey.column.action"), translate("hotkey.column.shortcut")]
        )
        self.table.setRowCount(len(self._actions))
        for row, action in enumerate(self._actions):
            shortcut = controller.hotkey_of(action)
            cell = QTableWidgetItem(shortcut or translate("hotkey.none"))
            if action in controller.failed_hotkeys:
                # Windows refused it: say so in the row, not only when it was set.
                cell.setText(translate("hotkey.not_working", shortcut=shortcut))
                cell.setForeground(_WARNING)
                cell.setToolTip(translate("hotkey.failed"))
            self.table.setItem(row, 0, QTableWidgetItem(controller.action_label(action)))
            self.table.setItem(row, 1, cell)
        self.table.resizeColumnToContents(0)
        self.table.selectRow(self._actions.index(keep) if keep in self._actions else -1)
        self.capture.setPlaceholderText(translate("hotkey.capture"))
        self.set_button.setText(translate("hotkey.set"))
        self.clear_button.setText(translate("hotkey.clear"))
        self.defaults_button.setText(translate("hotkey.restore_defaults"))
        self.help.setText(translate("hotkey.help"))
        self._selection_changed()

    def _apply(self, shortcut: str) -> None:
        action = self.selected()
        if not action:
            return
        self.message.setText(self.controller.set_hotkey(action, shortcut))
        if self.controller.hotkey_of(action) == shortcut:
            self.capture.clear()  # it was accepted, even if with a warning

    def set_shortcut(self) -> None:
        """Give the selected action the shortcut shown in the field."""
        if self.capture.text():
            self._apply(self.capture.text())

    def clear_shortcut(self) -> None:
        """Leave the selected action without a shortcut."""
        self._apply("")

    def restore_defaults(self) -> None:
        self.controller.restore_default_hotkeys()
        self.message.setText("")
        self.capture.clear()
