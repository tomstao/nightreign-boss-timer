"""What every page of the main window has in common, and the About page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from nightreign_boss_timer import __version__
from nightreign_boss_timer.ui.controller import Controller

REPOSITORY_URL = "https://github.com/tomstao/nightreign-boss-timer"


class Page(QWidget):
    """One page of the main window.

    ``key`` names the page: its sidebar text is the translation of ``page.<key>``. ``refresh``
    redraws everything from the settings in the current language. It is called when the page is
    shown and whenever the controller announces a change.
    """

    key = ""

    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller = controller

    def refresh(self) -> None:
        raise NotImplementedError


class AboutPage(Page):
    key = "about"

    def __init__(self, controller: Controller) -> None:
        super().__init__(controller)
        self.name = QLabel()
        self.name.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.version = QLabel()
        self.licence = QLabel()
        self.link = QLabel()
        self.link.setOpenExternalLinks(True)
        self.link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.safety = QLabel()
        self.safety.setWordWrap(True)
        self.disclaimer = QLabel()
        layout = QVBoxLayout(self)
        for label in (
            self.name,
            self.version,
            self.licence,
            self.link,
            self.safety,
            self.disclaimer,
        ):
            layout.addWidget(label)
        layout.addStretch(1)

    def refresh(self) -> None:
        translate = self.controller.translate
        self.name.setText(translate("app.name"))
        self.version.setText(translate("about.version", version=__version__))
        self.licence.setText(translate("about.licence"))
        self.link.setText(f'<a href="{REPOSITORY_URL}">{translate("about.repository")}</a>')
        self.safety.setText(translate("about.safety"))
        self.disclaimer.setText(translate("about.disclaimer"))
