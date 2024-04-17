# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional
import secrets

from PySide6 import QtWidgets, QtCore, QtGui

from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.encode import AudioTrack

from fastflix.flix import (
    generate_thumbnail_command,
)
from fastflix.encoders.common import helpers
from fastflix.resources import get_icon
from fastflix.language import t

__all__ = ["AudioConversion"]

logger = logging.getLogger("fastflix")

# audio_disposition_options = [
#     "dub",
#     "original",
#     "comment",
#     "visual_impaired",
# ]
#
# subtitle_disposition_options = [
#     "dub",
#     "original",
#     "comment",
#     "lyrics",
#     "karaoke",
#     "hearing_impaired",
# ]

channel_list = {
    "mono": 1,
    "stereo": 2,
    "2.1": 3,
    "3.0": 3,
    "3.0(back)": 3,
    "3.1": 4,
    "4.0": 4,
    "quad": 4,
    "quad(side)": 4,
    "5.0": 5,
    "5.1": 6,
    "6.0": 6,
    "6.0(front)": 6,
    "hexagonal": 6,
    "6.1": 7,
    "6.1(front)": 7,
    "7.0": 7,
    "7.0(front)": 7,
    "7.1": 8,
    "7.1(wide)": 8,
}


class AudioConversion(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, track_index, encoders):
        super().__init__(None)
        self.app = app
        self.setWindowTitle(f"Audio Conversion for Track {track_index}")
        self.setMinimumWidth(400)
        self.audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[track_index]

        # Conversion

        self.conversion_codec = QtWidgets.QComboBox()
        self.conversion_codec.addItems([t("None")] + list(sorted(encoders)))

        if self.audio_track.conversion_codec:
            self.conversion_codec.setCurrentText(self.audio_track.conversion_codec)
        self.conversion_codec.currentIndexChanged.connect(self.codec_changed)

        conversion_layout = QtWidgets.QHBoxLayout()
        conversion_layout.addWidget(QtWidgets.QLabel(t("Codec")))
        conversion_layout.addWidget(self.conversion_codec, 2)

        # AQ vs Bitrate

        self.aq = QtWidgets.QComboBox()
        self.aq.addItems(
            [
                f"0 - {t('Near Lossless')}",
                "1",
                f"2 - {t('High Quality')}",
                "3",
                f"4 - {t('Medium Quality')}",
                "5",
                f"6 {t('Low Quality')}",
                "7",
                "8",
                "9",
                t("Custom Bitrate"),
            ]
        )
        self.aq.setMinimumWidth(100)
        self.aq.currentIndexChanged.connect(self.set_aq)
        self.bitrate = QtWidgets.QLineEdit()
        self.bitrate.setFixedWidth(50)

        if self.audio_track.conversion_aq:
            self.aq.setCurrentIndex(self.audio_track.conversion_aq)
            self.bitrate.setDisabled(True)
        elif self.audio_track.conversion_bitrate:
            self.aq.setCurrentText(t("Custom Bitrate"))
            self.bitrate.setText(self.audio_track.conversion_bitrate)
            self.bitrate.setEnabled(True)

        elif self.conversion_codec.currentText() in ["libopus"]:
            self.aq.setCurrentIndex(10)
        else:
            self.aq.setCurrentIndex(3)

        quality_layout = QtWidgets.QHBoxLayout()
        quality_layout.addWidget(QtWidgets.QLabel(t("Audio Quality")))
        quality_layout.addWidget(self.aq, 1)
        quality_layout.addWidget(QtWidgets.QLabel(t("Bitrate")))
        quality_layout.addWidget(self.bitrate)
        quality_layout.addWidget(QtWidgets.QLabel("kb/s"))

        # Downmix

        self.downmix = QtWidgets.QComboBox()
        self.downmix.addItems([t("None")] + list(channel_list.keys()))
        self.downmix.setCurrentIndex(2)
        if self.audio_track.downmix:
            self.downmix.setCurrentText(self.audio_track.downmix)

        downmix_layout = QtWidgets.QHBoxLayout()
        downmix_layout.addWidget(QtWidgets.QLabel(t("Channel Layout")))
        downmix_layout.addWidget(self.downmix, 2)

        # Yes No

        yes_no_layout = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton(t("Cancel"))
        cancel.clicked.connect(self.close)
        yes_no_layout.addWidget(cancel)
        save = QtWidgets.QPushButton(t("Save"))
        save.clicked.connect(self.save)
        yes_no_layout.addWidget(save)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(conversion_layout)
        layout.addLayout(quality_layout)
        layout.addLayout(downmix_layout)
        layout.addLayout(yes_no_layout)

        self.setLayout(layout)

    def set_aq(self):
        index = self.aq.currentIndex()
        if index == 10:
            self.bitrate.setEnabled(True)
        else:
            self.bitrate.setDisabled(True)

    def codec_changed(self):
        if self.conversion_codec.currentText() in ["libopus"]:
            self.aq.setCurrentIndex(10)
            self.aq.setDisabled(True)
            # self.bitrate.setEnabled(True)
        else:
            self.aq.setEnabled(True)
            # self.bitrate.setDisabled(True)

    def save(self):
        if self.conversion_codec.currentIndex() != 0:
            self.audio_track.conversion_codec = self.conversion_codec.currentText()
        else:
            self.audio_track.conversion_codec = None

        if self.aq.currentIndex() != 10:
            self.audio_track.conversion_aq = self.aq.currentIndex()
            self.audio_track.conversion_bitrate = None
        else:
            self.audio_track.conversion_bitrate = self.bitrate.text()
            self.audio_track.conversion_aq = None

        if self.downmix.currentIndex() != 0:
            self.audio_track.downmix = self.downmix.currentText()
        else:
            self.audio_track.downmix = None

        self.close()