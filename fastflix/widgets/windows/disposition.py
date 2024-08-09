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
from fastflix.models.fastflix_app import FastFlixApp

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
    def __init__(self, app: FastFlixApp, parent, track_name, track_index, audio=True):
        super().__init__(None)
        self.parent = parent
        self.app = app
        self.track_name = track_name
        self.track_index = track_index
        self.audio = audio

        self.setMinimumWidth(200)

        self.forced = QtWidgets.QCheckBox(t("Forced"))

        self.default = QtWidgets.QCheckBox(t("Default"))

        track = self.get_track()
        self.forced.setChecked(track.dispositions.get("forced", False))
        self.default.setChecked(track.dispositions.get("default", False))

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

        for dis in audio_disposition_options if audio else subtitle_disposition_options:
            self.widgets[dis] = QtWidgets.QRadioButton(t(dis))
            group.addButton(self.widgets[dis])
            layout.addWidget(self.widgets[dis])

        for track_dis, is_set in track.dispositions.items():
            if is_set and track_dis in self.widgets.keys():
                self.widgets[track_dis].setChecked(True)

        self.parent.page_update()

        self.set_button = QtWidgets.QPushButton(t("Set"))
        self.set_button.clicked.connect(self.set_dispositions)
        layout.addWidget(self.set_button)

        self.setLayout(layout)

    def get_track(self):
        if self.audio:
            return self.app.fastflix.current_video.audio_tracks[self.track_index]
        return self.app.fastflix.current_video.subtitle_tracks[self.track_index]

    def set_dispositions(self):
        track = self.get_track()

        track.dispositions["forced"] = self.forced.isChecked()
        track.dispositions["default"] = self.default.isChecked()
        for dis in self.widgets:
            track.dispositions[dis] = self.widgets[dis].isChecked()
        self.parent.page_update()
        self.hide()

    def show(self):
        if self.audio:
            dispositions = self.app.fastflix.current_video.audio_tracks[self.track_index].dispositions
        else:
            dispositions = self.app.fastflix.current_video.subtitle_tracks[self.track_index].dispositions
        for dis in self.widgets:
            self.widgets[dis].setChecked(dispositions.get(dis, False))
        super().show()

    def close(self) -> bool:
        del self.parent
        del self.app
        del self.track_name
        del self.track_index
        del self.audio
        return super().close()
