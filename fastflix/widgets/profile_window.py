# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
from dataclasses import asdict

from iso639 import Lang
from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import x265Settings
from fastflix.shared import FastFlixInternalException, error_message
from fastflix.language import t

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())


class ProfileWindow(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, main, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.app = app
        self.main = main
        self.config_file = self.app.fastflix.config.config_path
        self.setWindowTitle(t("New Profile"))
        self.setMinimumSize(600, 200)
        layout = QtWidgets.QGridLayout()

        profile_name_label = QtWidgets.QLabel(t("Profile Name"))
        self.profile_name = QtWidgets.QLineEdit()

        self.auto_crop = QtWidgets.QCheckBox(t("Auto Crop"))

        audio_language_label = QtWidgets.QLabel(t("Audio select language"))
        self.audio_language = QtWidgets.QComboBox()
        self.audio_language.addItems([t("All"), t("None")] + language_list)
        self.audio_language.insertSeparator(1)
        self.audio_language.insertSeparator(3)

        sub_language_label = QtWidgets.QLabel(t("Subtitle select language"))
        self.sub_language = QtWidgets.QComboBox()
        self.sub_language.addItems([t("All"), t("None")] + language_list)
        self.sub_language.insertSeparator(1)
        self.sub_language.insertSeparator(3)

        sub_burn_in = QtWidgets.QCheckBox(t("Auto Burn-in first forced or default subtitle track"))

        self.encoder = x265Settings()
        self.encoder_settings = QtWidgets.QLabel()
        self.encoder_settings.setStyleSheet("font-family: monospace;")
        self.encoder_label = QtWidgets.QLabel(f"{t('Encoder')}: {self.encoder.name}")

        save_button = QtWidgets.QPushButton(t("Create Profile"))

        layout.addWidget(profile_name_label, 0, 0)
        layout.addWidget(self.profile_name, 0, 1)
        layout.addWidget(self.auto_crop, 1, 0)
        layout.addWidget(audio_language_label, 2, 0)
        layout.addWidget(self.audio_language, 2, 1)
        layout.addWidget(sub_language_label, 3, 0)
        layout.addWidget(self.sub_language, 3, 1)
        layout.addWidget(sub_burn_in, 4, 0, 1, 2)
        layout.addWidget(self.encoder_label, 5, 0, 1, 2)
        layout.addWidget(self.encoder_settings, 6, 0, 10, 2)
        layout.addWidget(save_button, 20, 1)

        self.update_settings()

        self.setLayout(layout)

    def update_settings(self):
        try:
            encoder = self.app.fastflix.current_video.video_settings.video_encoder_settings
        except AttributeError:
            pass
        else:
            if encoder:
                self.encoder = encoder
        settings = "\n".join(f"{k:<30} {v}" for k, v in asdict(self.encoder).items())
        self.encoder_label.setText(f"{t('Encoder')}: {self.encoder.name}")
        self.encoder_settings.setText(f"<pre>{settings}</pre>")
