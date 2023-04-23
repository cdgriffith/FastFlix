# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional
import secrets

from PySide6 import QtWidgets, QtCore, QtGui

from fastflix.flix import (
    generate_thumbnail_command,
)
from fastflix.encoders.common import helpers
from fastflix.resources import get_icon
from fastflix.language import t

__all__ = ["Disposition"]

logger = logging.getLogger("fastflix")

audio_disposition_options = [
    "dub",
    "original",
    "comment",
    "visual_impaired",
]

subtitle_disposition_options = [
    "dub",
    "original",
    "comment",
    "lyrics",
    "karaoke",
    "hearing_impaired",
]


class Disposition(QtWidgets.QWidget):
    def __init__(self, parent, track_name, subs=False):
        super().__init__(None)
        self.parent = parent
        self.track_name = track_name
        self.subs = subs
        self.dispositions = parent.dispositions

        self.forced = QtWidgets.QCheckBox(t("Forced"))

        self.default = QtWidgets.QCheckBox(t("Default"))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(track_name))
        layout.addWidget(self.default)
        layout.addWidget(self.forced)

        breaker_line = QtWidgets.QWidget()
        breaker_line.setMaximumHeight(2)
        breaker_line.setStyleSheet("background-color: #ccc; margin: auto 0; padding: auto 0;")

        self.widgets = {}

        layout.addWidget(breaker_line)

        group = QtWidgets.QButtonGroup(self)

        none_extra = QtWidgets.QRadioButton(t("No Extra"))
        none_extra.setChecked(True)
        group.addButton(none_extra)
        layout.addWidget(none_extra)

        if subs:
            for dis in subtitle_disposition_options:
                self.widgets[dis] = QtWidgets.QRadioButton(t(dis))
                group.addButton(self.widgets[dis])
                layout.addWidget(self.widgets[dis])
        else:
            for dis in audio_disposition_options:
                self.widgets[dis] = QtWidgets.QRadioButton(t(dis))
                group.addButton(self.widgets[dis])
                layout.addWidget(self.widgets[dis])

        self.set_button = QtWidgets.QPushButton(t("Set"))
        self.set_button.clicked.connect(self.set_dispositions)
        layout.addWidget(self.set_button)

        self.setLayout(layout)

    def set_dispositions(self):
        self.parent.dispositions["forced"] = self.forced.isChecked()
        self.parent.dispositions["default"] = self.default.isChecked()
        for dis in self.widgets:
            self.parent.dispositions[dis] = self.widgets[dis].isChecked()
        self.parent.set_dis_button()
        self.parent.page_update()
        self.hide()

    def show(self):
        self.forced.setChecked(self.parent.dispositions["forced"])
        self.default.setChecked(self.parent.dispositions["default"])
        for dis in self.widgets:
            self.widgets[dis].setChecked(self.parent.dispositions.get(dis, False))
        super().show()
