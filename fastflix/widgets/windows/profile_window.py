# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
import logging

from box import Box
from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.widgets.panels.abstract_list import FlixList
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
    NVEncCAVCSettings,
    FFmpegNVENCSettings,
    VCEEncCAVCSettings,
    VCEEncCSettings,
)
from fastflix.shared import error_message

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

logger = logging.getLogger("fastflix")


class AudioProfile(QtWidgets.QTabWidget):
    def __init__(self, parent_list, parent, index):
        super(AudioProfile, self).__init__(parent)
        self.enabled = True
        self.index = index
        self.parent = parent
        self.parent_list = parent_list
        self.match_type = QtWidgets.QComboBox()
        self.match_type.addItems(["All", "First", "Last"])
        self.match_type.currentIndexChanged.connect(self.update_combos)
        self.setFixedHeight(120)

        self.match_item = QtWidgets.QComboBox()
        self.match_item.addItems(["All", "Title", "Track Number", "Language", "Channels"])
        self.match_item.currentIndexChanged.connect(self.update_combos)

        self.match_input_boxes = [
            QtWidgets.QLineEdit("*"),
            QtWidgets.QLineEdit(""),
            QtWidgets.QComboBox(),
            QtWidgets.QComboBox(),
            QtWidgets.QComboBox(),
        ]
        self.match_input = self.match_input_boxes[0]
        self.match_input_boxes[0].setDisabled(True)
        self.match_input_boxes[1].setPlaceholderText(t("contains"))
        self.match_input_boxes[2].addItems([str(x) for x in range(1, 24)])
        self.match_input_boxes[3].addItems(language_list)
        self.match_input_boxes[3].setCurrentText("English")
        self.match_input_boxes[4].addItems(
            ["none | unknown", "mono", "stereo", "3 | 2.1", "4", "5", "6 | 5.1", "7", "8 | 7.1", "9", "10"]
        )

        self.kill_myself = QtWidgets.QPushButton("X")
        self.kill_myself.clicked.connect(lambda: self.parent_list.remove_track(self.index))

        # First Row
        self.grid = QtWidgets.QGridLayout()
        self.grid.addWidget(QtWidgets.QLabel(t("Match")), 0, 0)
        self.grid.addWidget(self.match_type, 0, 1)
        self.grid.addWidget(QtWidgets.QLabel(t("Select By")), 0, 2)
        self.grid.addWidget(self.match_item, 0, 3)
        self.grid.addWidget(self.match_input, 0, 4)
        self.grid.addWidget(self.kill_myself, 0, 5, 1, 5)

        self.downmix = QtWidgets.QComboBox()
        self.downmix.addItems([str(x) for x in range(1, 16)])
        self.downmix.setCurrentIndex(0)

        self.convert_to = QtWidgets.QComboBox()
        self.convert_to.addItems(["converters"])

        self.bitrate = QtWidgets.QComboBox()
        self.bitrate.addItems([str(x) for x in range(32, 1024, 32)])

        self.grid.addWidget(QtWidgets.QLabel(t("Conversion")), 1, 0)
        self.grid.addWidget(self.convert_to, 1, 1)
        self.grid.addWidget(QtWidgets.QLabel(t("Bitrate")), 1, 2)
        self.grid.addWidget(self.bitrate, 1, 3)
        self.grid.addWidget(self.downmix, 1, 4)

        self.setLayout(self.grid)

    def update_combos(self):
        # index = self.grid.indexOf(self.match_input)
        # print(index)
        # self.grid.removeWidget(self.match_input)
        self.match_input.hide()
        self.match_input = self.match_input_boxes[self.match_item.currentIndex()]

        self.grid.addWidget(self.match_input, 0, 4)
        self.match_input.show()

        # self.grid.replaceWidget(self.match_input, self.match_input_boxes[self.match_item.currentIndex()])
        #
        # self.match_input =
        # self.match_input.show()

    def set_outdex(self, pos):
        pass

    def set_first(self, pos):
        pass

    def set_last(self, pos):
        pass


class AudioSelect(FlixList):
    def __init__(self, app, parent):
        super().__init__(app, parent, "Audio Select", "audio")
        self.tracks = []

        self.passthrough_checkbox = QtWidgets.QCheckBox(t("Passthrough All"))
        self.add_button = QtWidgets.QPushButton(t("Add Pattern Match"))

        self.passthrough_checkbox.toggled.connect(self.passthrough_check)

        self.add_button.clicked.connect(self.add_track)

        layout = self.layout()
        # self.scroll_area = super().scroll_area
        layout.removeWidget(self.scroll_area)
        layout.addWidget(self.scroll_area, 3, 0, 4, 3)

        layout.addWidget(self.passthrough_checkbox, 0, 0)
        layout.addWidget(self.add_button, 0, 1)
        # self.passthrough_checkbox.setChecked(True)

        super()._new_source(self.tracks)

    def add_track(self):
        self.tracks.append(AudioProfile(self, self.inner_widget, len(self.tracks)))
        self.reorder(height=126)

    def remove_track(self, index):
        self.tracks.pop(index).close()
        for i, track in enumerate(self.tracks):
            track.index = i
        self.reorder(height=126)

    def passthrough_check(self):
        if self.passthrough_checkbox.isChecked():
            self.scroll_area.hide()
        else:
            self.scroll_area.show()

    def get_settings(self):
        if self.passthrough_checkbox.isChecked():
            return "PASSTHROUGH"
        filters = []
        for track in self.tracks:
            filters.append(
                {
                    "match_type": track.match_type.currentText(),
                    "match_item": track.match_item.currentText(),
                    "match_input": track.match_input.text(),
                }
            )
        return filters


class SubtitleSelect(FlixList):
    pass


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

        self.tab_area = QtWidgets.QTabWidget()
        self.tab_area.setMinimumWidth(500)
        self.tab_area.addTab(AudioSelect(self.app, self), "Audio Select")
        self.tab_area.addTab(SubtitleSelect(self.app, self, "Subtitle Select", "subtitles"), "Subtitle Select")

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
        layout.addWidget(self.tab_area, 0, 2, 20, 5)

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
            rotate=self.main.widgets.rotate.currentIndex(),
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
        elif isinstance(self.encoder, NVEncCAVCSettings):
            new_profile.nvencc_avc = self.encoder
        elif isinstance(self.encoder, FFmpegNVENCSettings):
            new_profile.ffmpeg_hevc_nvenc = self.encoder
        elif isinstance(self.encoder, VCEEncCSettings):
            new_profile.vceencc_hevc = self.encoder
        elif isinstance(self.encoder, VCEEncCAVCSettings):
            new_profile.vceencc_avc = self.encoder
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
        self.main.widgets.convert_to.setCurrentIndex(0)
