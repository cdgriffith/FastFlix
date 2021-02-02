# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
import logging

from box import Box
from iso639 import Lang
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.config import Profile, get_preset_defaults
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import (
    AOMAV1Settings,
    CopySettings,
    GIFSettings,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    NVEncCSettings,
    FFmpegNVENCSettings,
)
from fastflix.shared import error_message

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

logger = logging.getLogger("fastflix")


class ProfileWindow(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, main, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.app = app
        self.main = main
        self.config_file = self.app.fastflix.config.config_path
        self.setWindowTitle(t("New Profile"))
        self.setMinimumSize(500, 150)
        layout = QtWidgets.QGridLayout()

        profile_name_label = QtWidgets.QLabel(t("Profile Name"))
        self.profile_name = QtWidgets.QLineEdit()

        self.auto_crop = QtWidgets.QCheckBox(t("Auto Crop"))

        audio_language_label = QtWidgets.QLabel(t("Audio select language"))
        self.audio_language = QtWidgets.QComboBox()
        self.audio_language.addItems([t("All"), t("None")] + language_list)
        self.audio_language.insertSeparator(1)
        self.audio_language.insertSeparator(3)
        self.audio_first_only = QtWidgets.QCheckBox(t("Only select first matching Audio Track"))

        sub_language_label = QtWidgets.QLabel(t("Subtitle select language"))
        self.sub_language = QtWidgets.QComboBox()
        self.sub_language.addItems([t("All"), t("None")] + language_list)
        self.sub_language.insertSeparator(1)
        self.sub_language.insertSeparator(3)
        self.sub_first_only = QtWidgets.QCheckBox(t("Only select first matching Subtitle Track"))

        self.sub_burn_in = QtWidgets.QCheckBox(t("Auto Burn-in first forced or default subtitle track"))

        self.encoder = x265Settings(crf=18)
        self.encoder_settings = QtWidgets.QLabel()
        self.encoder_settings.setStyleSheet("font-family: monospace;")
        self.encoder_label = QtWidgets.QLabel(f"{t('Encoder')}: {self.encoder.name}")

        save_button = QtWidgets.QPushButton(t("Create Profile"))
        save_button.clicked.connect(self.save)
        save_button.setMaximumWidth(150)

        layout.addWidget(profile_name_label, 0, 0)
        layout.addWidget(self.profile_name, 0, 1)
        layout.addWidget(self.auto_crop, 1, 0)
        layout.addWidget(audio_language_label, 2, 0)
        layout.addWidget(self.audio_language, 2, 1)
        layout.addWidget(self.audio_first_only, 3, 1)
        layout.addWidget(sub_language_label, 4, 0)
        layout.addWidget(self.sub_language, 4, 1)
        layout.addWidget(self.sub_first_only, 5, 1)
        layout.addWidget(self.sub_burn_in, 6, 0, 1, 2)
        layout.addWidget(self.encoder_label, 7, 0, 1, 2)
        layout.addWidget(self.encoder_settings, 8, 0, 10, 2)
        layout.addWidget(save_button, 20, 1, alignment=QtCore.Qt.AlignRight)

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
        settings = "\n".join(f"{k:<30} {v}" for k, v in self.encoder.dict().items())
        self.encoder_label.setText(f"{t('Encoder')}: {self.encoder.name}")
        self.encoder_settings.setText(f"<pre>{settings}</pre>")

    def save(self):
        profile_name = self.profile_name.text().strip()
        if not profile_name:
            return error_message(t("Please provide a profile name"))
        if profile_name in self.app.fastflix.config.profiles:
            return error_message(f'{t("Profile")} {self.profile_name.text().strip()} {t("already exists")}')

        audio_lang = "en"
        audio_select = True
        audio_select_preferred_language = False
        if self.audio_language.currentIndex() == 2:  # None
            audio_select_preferred_language = False
            audio_select = False
        elif self.audio_language.currentIndex() != 0:
            audio_select_preferred_language = True
            audio_lang = Lang(self.audio_language.currentText()).pt2b

        sub_lang = "en"
        subtitle_select = True
        subtitle_select_preferred_language = False
        if self.sub_language.currentIndex() == 2:  # None
            subtitle_select_preferred_language = False
            subtitle_select = False
        elif self.sub_language.currentIndex() != 0:
            subtitle_select_preferred_language = True
            sub_lang = Lang(self.sub_language.currentText()).pt2b

        v_flip, h_flip = self.main.get_flips()

        new_profile = Profile(
            auto_crop=self.auto_crop.isChecked(),
            keep_aspect_ratio=self.main.widgets.scale.keep_aspect.isChecked(),
            fast_seek=self.main.fast_time,
            rotate=self.main.rotation_to_transpose(),
            vertical_flip=v_flip,
            horizontal_flip=h_flip,
            copy_chapters=self.main.copy_chapters,
            remove_metadata=self.main.remove_metadata,
            remove_hdr=self.main.remove_hdr,
            audio_language=audio_lang,
            audio_select=audio_select,
            audio_select_preferred_language=audio_select_preferred_language,
            audio_select_first_matching=self.audio_first_only.isChecked(),
            subtitle_language=sub_lang,
            subtitle_select=subtitle_select,
            subtitle_automatic_burn_in=self.sub_burn_in.isChecked(),
            subtitle_select_preferred_language=subtitle_select_preferred_language,
            subtitle_select_first_matching=self.sub_first_only.isChecked(),
            encoder=self.encoder.name,
        )

        if isinstance(self.encoder, x265Settings):
            new_profile.x265 = self.encoder
        elif isinstance(self.encoder, x264Settings):
            new_profile.x264 = self.encoder
        elif isinstance(self.encoder, rav1eSettings):
            new_profile.rav1e = self.encoder
        elif isinstance(self.encoder, SVTAV1Settings):
            new_profile.svt_av1 = self.encoder
        elif isinstance(self.encoder, VP9Settings):
            new_profile.vp9 = self.encoder
        elif isinstance(self.encoder, AOMAV1Settings):
            new_profile.aom_av1 = self.encoder
        elif isinstance(self.encoder, GIFSettings):
            new_profile.gif = self.encoder
        elif isinstance(self.encoder, WebPSettings):
            new_profile.webp = self.encoder
        elif isinstance(self.encoder, CopySettings):
            new_profile.copy_settings = self.encoder
        elif isinstance(self.encoder, NVEncCSettings):
            new_profile.nvencc_hevc = self.encoder
        elif isinstance(self.encoder, FFmpegNVENCSettings):
            new_profile.ffmpeg_hevc_nvenc = self.encoder
        else:
            logger.error("Profile cannot be saved! Unknown encoder type.")
            return

        self.app.fastflix.config.profiles[profile_name] = new_profile
        self.app.fastflix.config.selected_profile = profile_name
        self.app.fastflix.config.save()
        self.main.widgets.profile_box.addItem(profile_name)
        self.main.widgets.profile_box.setCurrentText(profile_name)
        self.hide()

    def delete_current_profile(self):
        if self.app.fastflix.config.selected_profile in get_preset_defaults():
            return error_message(
                f"{self.app.fastflix.config.selected_profile} " f"{t('is a default profile and will not be removed')}"
            )
        self.main.loading_video = True
        del self.app.fastflix.config.profiles[self.app.fastflix.config.selected_profile]
        self.app.fastflix.config.selected_profile = "Standard Profile"
        self.app.fastflix.config.save()
        self.main.widgets.profile_box.clear()
        self.main.widgets.profile_box.addItems(self.app.fastflix.config.profiles.keys())
        self.main.loading_video = False
        self.main.widgets.profile_box.setCurrentText("Standard Profile")
