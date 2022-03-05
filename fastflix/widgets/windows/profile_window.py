# -*- coding: utf-8 -*-

import logging

from box import Box
from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.flix import ffmpeg_valid_color_primaries, ffmpeg_valid_color_transfers, ffmpeg_valid_color_space
from fastflix.language import t
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.models.config import get_preset_defaults
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.encode import (
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
from fastflix.models.profiles import AudioMatch, Profile, MatchItem, MatchType, AdvancedOptions
from fastflix.shared import error_message

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

logger = logging.getLogger("fastflix")

match_type_eng = [MatchType.ALL, MatchType.FIRST, MatchType.LAST]
match_type_locale = [t("All"), t("First"), t("Last")]

match_item_enums = [MatchItem.ALL, MatchItem.TITLE, MatchItem.TRACK, MatchItem.LANGUAGE, MatchItem.CHANNELS]
match_item_locale = [t("All"), t("Title"), t("Track Number"), t("Language"), t("Channels")]

sub_match_item_enums = [MatchItem.ALL, MatchItem.TRACK, MatchItem.LANGUAGE]
sub_match_item_locale = [t("All"), t("Track Number"), t("Language")]


class AudioProfile(QtWidgets.QTabWidget):
    def __init__(self, parent_list, app, parent, index):
        super(AudioProfile, self).__init__(parent)
        self.enabled = True
        self.index = index
        self.parent = parent
        self.parent_list = parent_list
        self.match_type = QtWidgets.QComboBox()
        self.match_type.addItems(match_type_locale)
        self.match_type.currentIndexChanged.connect(self.update_combos)
        self.setFixedHeight(120)

        self.match_item = QtWidgets.QComboBox()
        self.match_item.addItems(match_item_locale)
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
        self.downmix.addItems(["No Downmix"] + [str(x) for x in range(1, 16)])
        self.downmix.setCurrentIndex(0)

        self.convert_to = QtWidgets.QComboBox()
        self.convert_to.addItems(["None | Passthrough"] + app.fastflix.audio_encoders)
        self.convert_to.currentIndexChanged.connect(self.update_conversion)

        self.bitrate = QtWidgets.QComboBox()
        self.bitrate.addItems([str(x) for x in range(32, 1024, 32)])

        self.bitrate.setDisabled(True)
        self.downmix.setDisabled(True)

        self.grid.addWidget(QtWidgets.QLabel(t("Conversion")), 1, 0)
        self.grid.addWidget(self.convert_to, 1, 1)
        self.grid.addWidget(QtWidgets.QLabel(t("Bitrate")), 1, 2)
        self.grid.addWidget(self.bitrate, 1, 3)
        self.grid.addWidget(self.downmix, 1, 4)
        self.grid.setColumnStretch(3, 0)
        self.grid.setColumnStretch(4, 0)
        self.grid.setColumnStretch(5, 0)

        self.setLayout(self.grid)

    def update_combos(self):
        self.match_input.hide()
        self.match_input = self.match_input_boxes[self.match_item.currentIndex()]

        self.grid.addWidget(self.match_input, 0, 4)
        self.match_input.show()

    def update_conversion(self):
        if self.convert_to.currentIndex() == 0:
            self.bitrate.setDisabled(True)
            self.downmix.setDisabled(True)
        else:
            self.bitrate.setEnabled(True)
            self.downmix.setEnabled(True)

    def set_outdex(self, pos):
        pass

    def set_first(self, pos):
        pass

    def set_last(self, pos):
        pass

    def get_settings(self):
        match_item_enum = match_item_enums[self.match_item.currentIndex()]
        if match_item_enum in (MatchItem.ALL, MatchItem.TITLE):
            match_input_value = self.match_input.text()
        elif match_item_enum == MatchItem.TRACK:
            match_input_value = self.match_input.currentText()
        elif match_item_enum == MatchItem.LANGUAGE:
            match_input_value = Lang(self.match_input.currentText()).pt2b
        elif match_item_enum == MatchItem.CHANNELS:
            match_input_value = str(self.match_input.currentIndex())
        else:
            raise Exception("Internal error, what do we do sir?")

        return AudioMatch(
            match_type=match_type_eng[self.match_type.currentIndex()],
            match_item=match_item_enum,
            match_input=match_input_value,
            conversion=self.convert_to.currentText() if self.convert_to.currentIndex() > 0 else None,
            bitrate=self.bitrate.currentText(),
            downmix=self.bitrate.currentIndex(),
        )


class AudioSelect(FlixList):
    def __init__(self, app, parent):
        super().__init__(app, parent, "Audio Select", "Audio")
        self.tracks = []

        self.passthrough_checkbox = QtWidgets.QCheckBox(t("Passthrough All"))
        self.add_button = QtWidgets.QPushButton(f'  {t("Add Pattern Match")}  ')
        if self.app.fastflix.config.theme == "onyx":
            self.add_button.setStyleSheet("border-radius: 10px;")

        self.passthrough_checkbox.toggled.connect(self.passthrough_check)

        self.add_button.clicked.connect(self.add_track)

        layout = self.layout()
        # self.scroll_area = super().scroll_area
        layout.removeWidget(self.scroll_area)

        layout.addWidget(self.passthrough_checkbox, 0, 0)
        layout.addWidget(self.add_button, 0, 1, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.scroll_area, 1, 0, 1, 2)
        self.passthrough_checkbox.setChecked(True)
        # self.passthrough_checkbox.setChecked(True)
        super()._new_source(self.tracks)

    def add_track(self):
        self.tracks.append(AudioProfile(self, self.app, self.inner_widget, len(self.tracks)))
        self.reorder(height=126)

    def remove_track(self, index):
        self.tracks.pop(index).close()
        for i, track in enumerate(self.tracks):
            track.index = i
        self.reorder(height=126)

    def passthrough_check(self):
        if self.passthrough_checkbox.isChecked():
            self.scroll_area.setDisabled(True)
            self.add_button.setDisabled(True)
        else:
            self.scroll_area.setEnabled(True)
            self.add_button.setEnabled(True)

    def get_settings(self):
        if self.passthrough_checkbox.isChecked():
            return None
        filters = []
        for track in self.tracks:
            filters.append(track.get_settings())
        return filters


class SubtitleSelect(QtWidgets.QWidget):
    def __init__(self, app, parent):
        super().__init__()

        self.app = app
        self.parent = parent

        sub_language_label = QtWidgets.QLabel(t("Subtitle select language"))
        self.sub_language = QtWidgets.QComboBox()
        self.sub_language.addItems([t("All"), t("None")] + language_list)
        self.sub_language.insertSeparator(1)
        self.sub_language.insertSeparator(3)
        self.sub_language.setFixedWidth(250)
        self.sub_first_only = QtWidgets.QCheckBox(t("Only select first matching Subtitle Track"))

        self.sub_burn_in = QtWidgets.QCheckBox(t("Auto Burn-in first forced or default subtitle track"))

        layout = QtWidgets.QGridLayout()
        layout.addWidget(sub_language_label, 0, 0)
        layout.addWidget(self.sub_language, 0, 1)
        layout.addWidget(self.sub_first_only, 1, 0)
        layout.addWidget(self.sub_burn_in, 2, 0, 1, 2)
        layout.addWidget(QtWidgets.QWidget(), 3, 0, 1, 2)
        layout.setRowStretch(3, True)
        self.setLayout(layout)


class AdvancedTab(QtWidgets.QTabWidget):
    def __init__(self, advanced_settings):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel()

        self.color_primaries_widget = QtWidgets.QComboBox()
        self.color_primaries_widget.addItem(t("Unspecified"))
        self.color_primaries_widget.addItems(ffmpeg_valid_color_primaries)

        self.color_transfer_widget = QtWidgets.QComboBox()
        self.color_transfer_widget.addItem(t("Unspecified"))
        self.color_transfer_widget.addItems(ffmpeg_valid_color_transfers)

        self.color_space_widget = QtWidgets.QComboBox()
        self.color_space_widget.addItem(t("Unspecified"))
        self.color_space_widget.addItems(ffmpeg_valid_color_space)

        primaries_layout = QtWidgets.QHBoxLayout()
        primaries_layout.addWidget(QtWidgets.QLabel(t("Color Primaries")))
        primaries_layout.addWidget(self.color_primaries_widget)

        transfer_layout = QtWidgets.QHBoxLayout()
        transfer_layout.addWidget(QtWidgets.QLabel(t("Color Transfer")))
        transfer_layout.addWidget(self.color_transfer_widget)

        space_layout = QtWidgets.QHBoxLayout()
        space_layout.addWidget(QtWidgets.QLabel(t("Color Space")))
        space_layout.addWidget(self.color_space_widget)

        layout.addLayout(primaries_layout)
        layout.addLayout(transfer_layout)
        layout.addLayout(space_layout)
        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.text_update(advanced_settings)
        self.setLayout(layout)

    def text_update(self, advanced_settings):
        ignored = ("color_primaries", "color_transfer", "color_space", "denoise_type_index", "denoise_strength_index")
        settings = "\n".join(f"{k:<30} {v}" for k, v in advanced_settings.dict().items() if k not in ignored)
        self.label.setText(f"<pre>{settings}</pre>")


class PrimaryOptions(QtWidgets.QTabWidget):
    def __init__(self, main_options):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel()
        settings = "\n".join(f"{k:<30} {v}" for k, v in main_options.items())
        self.label.setText(f"<pre>{settings}</pre>")

        self.auto_crop = QtWidgets.QCheckBox(t("Auto Crop"))

        layout.addWidget(self.auto_crop)
        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.setLayout(layout)


class EncoderOptions(QtWidgets.QTabWidget):
    def __init__(self, app, main):
        super().__init__()
        self.main = main
        self.app = app
        self.label = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.label)
        layout.addStretch(1)

        self.update_settings()

        self.setLayout(layout)

    def update_settings(self):
        settings = "\n".join(f"{k:<30} {v}" for k, v in self.main.encoder.dict().items())
        self.label.setText(f"<pre>{settings}</pre>")


class ProfileWindow(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, main, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.app = app
        self.main = main
        self.config_file = self.app.fastflix.config.config_path
        self.setWindowTitle(t("New Profile"))
        self.setMinimumSize(500, 450)
        layout = QtWidgets.QGridLayout()

        profile_name_label = QtWidgets.QLabel(t("Profile Name"))
        profile_name_label.setFixedHeight(40)
        self.profile_name = QtWidgets.QLineEdit()
        if self.app.fastflix.config.theme == "onyx":
            self.profile_name.setStyleSheet("background-color: #707070; border-radius: 10px; color: black")
        self.profile_name.setFixedWidth(300)

        self.advanced_options: AdvancedOptions = main.video_options.advanced.get_settings()

        self.encoder = x265Settings(crf=18)

        theme = "QPushButton{ padding: 0 10px; font-size: 14px;  }"
        if self.app.fastflix.config.theme in ("dark", "onyx"):
            theme = """
            QPushButton {
              padding: 0 10px;
              font-size: 14px;
              background-color: #4f4f4f;
              border: none;
              border-radius: 10px;
              color: white; }
            QPushButton:hover {
              background-color: #6b6b6b; }"""

        save_button = QtWidgets.QPushButton(t("Create Profile"))
        save_button.setStyleSheet(theme)
        save_button.clicked.connect(self.save)
        save_button.setMaximumWidth(150)
        save_button.setFixedHeight(60)

        v_flip, h_flip = self.main.get_flips()
        self.main_settings = Box(
            keep_aspect_ratio=self.main.widgets.scale.keep_aspect.isChecked(),
            fast_seek=self.main.fast_time,
            rotate=self.main.widgets.rotate.currentIndex(),
            vertical_flip=v_flip,
            horizontal_flip=h_flip,
            copy_chapters=self.main.copy_chapters,
            remove_metadata=self.main.remove_metadata,
            remove_hdr=self.main.remove_hdr,
        )

        self.tab_area = QtWidgets.QTabWidget()
        self.tab_area.setMinimumWidth(500)
        self.audio_select = AudioSelect(self.app, self)
        self.subtitle_select = SubtitleSelect(self.app, self)
        self.advanced_tab = AdvancedTab(self.advanced_options)
        self.primary_tab = PrimaryOptions(self.main_settings)
        self.encoder_tab = EncoderOptions(self.app, self)
        self.tab_area.addTab(self.primary_tab, "Primary Settings")
        self.tab_area.addTab(self.encoder_tab, "Video")
        self.tab_area.addTab(self.audio_select, "Audio")
        self.tab_area.addTab(self.subtitle_select, "Subtitles")
        self.tab_area.addTab(self.advanced_tab, "Advanced Options")
        # self.tab_area.addTab(self.subtitle_select, "Subtitles")
        # self.tab_area.addTab(SubtitleSelect(self.app, self, "Subtitle Select", "subtitles"), "Subtitle Select")

        layout.addWidget(profile_name_label, 0, 0)
        layout.addWidget(self.profile_name, 0, 1, 1, 2, alignment=QtCore.Qt.AlignCenter)
        # layout.addWidget(self.auto_crop, 1, 0)
        # layout.addWidget(audio_language_label, 2, 0)
        # layout.addWidget(self.audio_language, 2, 1)
        # layout.addWidget(self.audio_first_only, 3, 1)
        # layout.addWidget(self.encoder_label, 7, 0, 1, 2)
        # layout.addWidget(self.encoder_settings, 8, 0, 10, 2)
        layout.addWidget(save_button, 0, 5, alignment=QtCore.Qt.AlignRight)

        layout.addWidget(self.tab_area, 1, 0, 20, 6)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
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
        self.encoder_tab.update_settings()
        self.advanced_options = self.main.video_options.advanced.get_settings()
        self.advanced_tab.text_update(self.advanced_options)

    def save(self):
        profile_name = self.profile_name.text().strip()
        if not profile_name:
            return error_message(t("Please provide a profile name"))
        if profile_name in self.app.fastflix.config.profiles:
            return error_message(f'{t("Profile")} {self.profile_name.text().strip()} {t("already exists")}')

        sub_lang = "en"
        subtitle_enabled = True
        subtitle_select_preferred_language = False
        if self.subtitle_select.sub_language.currentIndex() == 2:  # None
            subtitle_select_preferred_language = False
            subtitle_enabled = False
        elif self.subtitle_select.sub_language.currentIndex() != 0:
            subtitle_select_preferred_language = True
            sub_lang = Lang(self.subtitle_select.sub_language.currentText()).pt2b

        self.advanced_options.color_space = (
            None
            if self.advanced_tab.color_space_widget.currentIndex() == 0
            else self.advanced_tab.color_space_widget.currentText()
        )
        self.advanced_options.color_transfer = (
            None
            if self.advanced_tab.color_transfer_widget.currentIndex() == 0
            else self.advanced_tab.color_transfer_widget.currentText()
        )
        self.advanced_options.color_primaries = (
            None
            if self.advanced_tab.color_primaries_widget.currentIndex() == 0
            else self.advanced_tab.color_primaries_widget.currentText()
        )

        new_profile = Profile(
            profile_version=2,
            auto_crop=self.primary_tab.auto_crop.isChecked(),
            keep_aspect_ratio=self.main_settings.keep_aspect_ratio,
            fast_seek=self.main_settings.fast_seek,
            rotate=self.main_settings.rotate,
            vertical_flip=self.main_settings.vertical_flip,
            horizontal_flip=self.main_settings.horizontal_flip,
            copy_chapters=self.main_settings.copy_chapters,
            remove_metadata=self.main_settings.remove_metadata,
            remove_hdr=self.main_settings.remove_hdr,
            audio_filters=self.audio_select.get_settings(),
            # subtitle_filters=self.subtitle_select.get_settings(),
            subtitle_language=sub_lang,
            subtitle_select=subtitle_enabled,
            subtitle_automatic_burn_in=self.subtitle_select.sub_burn_in.isChecked(),
            subtitle_select_preferred_language=subtitle_select_preferred_language,
            subtitle_select_first_matching=self.subtitle_select.sub_first_only.isChecked(),
            encoder=self.encoder.name,
            advanced_options=self.advanced_options,
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
