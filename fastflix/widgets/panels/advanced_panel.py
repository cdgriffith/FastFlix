#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import VideoSettings
from fastflix.resources import get_icon
from fastflix.models.profiles import AdvancedOptions
from fastflix.flix import ffmpeg_valid_color_primaries, ffmpeg_valid_color_transfers, ffmpeg_valid_color_space

logger = logging.getLogger("fastflix")

video_speeds = {
    t("Same as Source"): 1,
    "1/100": 100,
    "1/10": 10,
    # "1/5": 5,
    "1/4": 4,
    # "1/3": 3,
    "1/2": 2,
    # "2/3": 1.67,
    # "3/4": 1.5,
    # "1.5x": 0.75,
    "2x": 0.5,
    # "3x": 0.34,
    "4x": 0.25,
    # "5x": 0.2,
    "10x": 0.1,
    "100x": 0.01,
}

denoise_presets = {
    "nlmeans": {
        "weak": "nlmeans=s=1.0:p=3:r=9",
        "moderate": "nlmeans=s=1.0:p=7:r=15",
        "strong": "nlmeans=s=10.0:p=13:r=25",
    },
    "atadenoise": {
        "weak": "atadenoise=0a=0.01:0b=0.02:1a=0.01:1b=0.02:2a=0.01:2b=0.02:s=9",
        "moderate": "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=9",
        "strong": "atadenoise=0a=0.04:0b=0.12:1a=0.04:1b=0.12:2a=0.04:2b=0.12:s=9",
    },
    "hqdn3d": {
        "weak": "hqdn3d=luma_spatial=2:chroma_spatial=1.5:luma_tmp=3:chroma_tmp=2.25",
        "moderate": "hqdn3d=luma_spatial=4:chroma_spatial=3:luma_tmp=6:chroma_tmp=4.5",
        "strong": "hqdn3d=luma_spatial=10:chroma_spatial=7.5:luma_tmp=15:chroma_tmp=11.25",
    },
    "vaguedenoiser": {
        "weak": "vaguedenoiser=threshold=1:method=soft:nsteps=5",
        "moderate": "vaguedenoiser=threshold=3:method=soft:nsteps=5",
        "strong": "vaguedenoiser=threshold=6:method=soft:nsteps=5",
    },
}

vsync = ["auto", "passthrough", "cfr", "vfr", "drop"]
tone_map_items = ["none", "clip", "linear", "gamma", "reinhard", "hable", "mobius"]


def non(value):
    if value.lower() in (
        t("none").lower(),
        "none",
        t("Unspecified").lower(),
        "unspecified",
        t("Same as Source").lower(),
        "same as source",
    ):
        return None
    return value


def get_key(my_dict, val):
    for key, value in my_dict.items():
        if val == value:
            return key
    return None


class AdvancedPanel(QtWidgets.QWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()
        self.updating = False
        self.only_int = QtGui.QIntValidator()

        self.layout = QtWidgets.QGridLayout()

        self.last_row = 0

        self.init_fps()
        self.add_spacer()
        self.init_video_speed()
        self.add_spacer()
        self.init_eq()
        self.add_spacer()
        self.init_denoise()
        self.add_spacer()
        self.init_deblock()
        self.add_spacer()
        self.init_color_info()
        self.add_spacer()
        self.init_vbv()
        self.add_spacer()
        self.layout.setRowStretch(self.last_row, True)
        self.init_hw_message()
        self.init_titles()
        # self.add_spacer()
        # self.init_custom_filters()

        # self.last_row += 1

        # self.layout.setColumnStretch(6, True)
        self.last_row += 1

        warning_label = QtWidgets.QLabel()
        ico = QtGui.QIcon(get_icon("onyx-warning", app.fastflix.config.theme))
        warning_label.setPixmap(ico.pixmap(22))

        for i in range(1, 7):
            self.layout.setColumnMinimumWidth(i, 155)
        self.setLayout(self.layout)

    def add_spacer(self):
        self.last_row += 1
        spacer_widget = QtWidgets.QWidget(self)
        spacer_widget.setFixedHeight(1)
        spacer_widget.setStyleSheet("background-color: #ddd")
        self.layout.addWidget(spacer_widget, self.last_row, 0, 1, 7)

    def add_row_label(self, label, row_number):
        label = QtWidgets.QLabel(label)
        label.setFixedWidth(100)
        if self.app.fastflix.config.theme == "onyx":
            label.setStyleSheet("color: #b5b5b5")
        self.layout.addWidget(label, row_number, 0, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def init_fps(self):
        self.incoming_fps_widget = QtWidgets.QLineEdit()
        self.incoming_fps_widget.setFixedWidth(150)
        self.incoming_fps_widget.setDisabled(True)
        self.incoming_fps_widget.textChanged.connect(self.page_update)
        self.outgoing_fps_widget = QtWidgets.QLineEdit()
        self.outgoing_fps_widget.setFixedWidth(150)
        self.outgoing_fps_widget.setDisabled(True)
        self.outgoing_fps_widget.textChanged.connect(self.page_update)
        self.incoming_same_as_source = QtWidgets.QCheckBox(t("Same as Source"))
        self.incoming_same_as_source.setChecked(True)
        self.incoming_same_as_source.toggled.connect(
            lambda: self.fps_update(self.incoming_same_as_source, self.incoming_fps_widget)
        )
        self.outgoing_same_as_source = QtWidgets.QCheckBox(t("Same as Source"))
        self.outgoing_same_as_source.setChecked(True)
        self.outgoing_same_as_source.toggled.connect(
            lambda: self.fps_update(self.outgoing_same_as_source, self.outgoing_fps_widget)
        )

        self.source_frame_rate = QtWidgets.QLabel("")
        self.vsync_widget = QtWidgets.QComboBox()
        self.vsync_widget.addItem(t("Unspecified"))
        self.vsync_widget.addItems(vsync)
        self.vsync_widget.currentIndexChanged.connect(self.page_update)

        self.add_row_label(t("Frame Rate"), self.last_row)

        self.layout.addWidget(
            QtWidgets.QLabel(t("Override Source FPS")), self.last_row, 1, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.incoming_fps_widget, self.last_row, 2)
        self.layout.addWidget(self.incoming_same_as_source, self.last_row, 3)
        self.layout.addWidget(
            QtWidgets.QLabel(t("Source Frame Rate")), self.last_row, 5, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.source_frame_rate, self.last_row, 6)

        self.last_row += 1
        self.layout.addWidget(
            QtWidgets.QLabel(t("Output FPS") + " ʘ"), self.last_row, 1, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.outgoing_fps_widget, self.last_row, 2)
        self.layout.addWidget(self.outgoing_same_as_source, self.last_row, 3)

        self.layout.addWidget(QtWidgets.QLabel(t("vsync")), self.last_row, 5, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.vsync_widget, self.last_row, 6)

        self.last_row += 1

    def fps_update(self, myself, widget):
        widget.setDisabled(myself.isChecked())
        self.page_update()

    # def init_concat(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     self.concat_widget = QtWidgets.QCheckBox(t("Combine Files"))
    #     # TODO add "learn more" link
    #
    #     layout.addWidget(self.concat_widget)
    #     return layout

    def init_video_speed(self):
        self.last_row += 1
        self.video_speed_widget = QtWidgets.QComboBox()
        self.video_speed_widget.addItems(video_speeds.keys())
        self.video_speed_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(
            QtWidgets.QLabel(t("Video Speed") + " ʘ"), self.last_row, 1, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.video_speed_widget, self.last_row, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Warning: Audio will not be modified")), self.last_row, 3, 1, 3)

        # def init_tone_map(self):
        #     self.last_row += 1
        self.tone_map_widget = QtWidgets.QComboBox()
        self.tone_map_widget.addItems(tone_map_items)
        self.tone_map_widget.setCurrentIndex(5)
        self.tone_map_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(
            QtWidgets.QLabel(t("HDR -> SDR Tone Map")), self.last_row, 5, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.tone_map_widget, self.last_row, 6)

    def init_eq(self):
        self.last_row += 1
        self.brightness_widget = QtWidgets.QLineEdit()
        self.brightness_widget.setValidator(QtGui.QDoubleValidator())
        self.brightness_widget.setToolTip("Default is: 0")
        self.brightness_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.contrast_widget = QtWidgets.QLineEdit()
        self.contrast_widget.setValidator(QtGui.QDoubleValidator())
        self.contrast_widget.setToolTip("Default is: 1")
        self.contrast_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.saturation_widget = QtWidgets.QLineEdit()
        self.saturation_widget.setValidator(QtGui.QDoubleValidator())
        self.saturation_widget.setToolTip("Default is: 1")
        self.saturation_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.add_row_label(t("Equalizer") + " ʘ", self.last_row)

        self.layout.addWidget(QtWidgets.QLabel(t("Brightness")), self.last_row, 1, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.brightness_widget, self.last_row, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Contrast")), self.last_row, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.contrast_widget, self.last_row, 4)
        self.layout.addWidget(QtWidgets.QLabel(t("Saturation")), self.last_row, 5, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.saturation_widget, self.last_row, 6)

    def init_denoise(self):
        self.last_row += 1
        self.denoise_type_widget = QtWidgets.QComboBox()
        self.denoise_type_widget.addItems(["none", "nlmeans", "atadenoise", "hqdn3d", "vaguedenoiser"])
        self.denoise_type_widget.setCurrentIndex(0)
        self.denoise_type_widget.currentIndexChanged.connect(self.page_update)

        self.denoise_strength_widget = QtWidgets.QComboBox()
        self.denoise_strength_widget.addItems(["weak", "moderate", "strong"])
        self.denoise_strength_widget.setCurrentIndex(0)
        self.denoise_strength_widget.currentIndexChanged.connect(self.page_update)

        self.add_row_label(t("Denoise") + " ʘ", self.last_row)
        self.layout.addWidget(QtWidgets.QLabel(t("Method")), self.last_row, 1, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_type_widget, self.last_row, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Strength")), self.last_row, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_strength_widget, self.last_row, 4)

    def init_deblock(self):
        self.last_row += 1
        self.deblock_widget = QtWidgets.QComboBox()
        self.deblock_widget.addItems(["none", "weak", "strong"])
        self.deblock_widget.setCurrentIndex(0)
        self.deblock_widget.currentIndexChanged.connect(self.page_update)

        self.deblock_size_widget = QtWidgets.QComboBox()
        self.deblock_size_widget.addItem("4")
        self.deblock_size_widget.addItems([str(x * 4) for x in range(2, 33, 2)])
        self.deblock_size_widget.addItems(["256", "512"])
        self.deblock_size_widget.currentIndexChanged.connect(self.page_update)
        self.deblock_size_widget.setCurrentIndex(2)

        self.add_row_label(t("Deblock") + " ʘ", self.last_row)
        self.layout.addWidget(QtWidgets.QLabel(t("Strength")), self.last_row, 1, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_widget, self.last_row, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Block Size")), self.last_row, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_size_widget, self.last_row, 4)

    def init_color_info(self):
        self.last_row += 1
        self.color_primaries_widget = QtWidgets.QComboBox()
        self.color_primaries_widget.addItem(t("Unspecified"))
        self.color_primaries_widget.addItems(ffmpeg_valid_color_primaries)
        self.color_primaries_widget.currentIndexChanged.connect(self.page_update)

        self.color_transfer_widget = QtWidgets.QComboBox()
        self.color_transfer_widget.addItem(t("Unspecified"))
        self.color_transfer_widget.addItems(ffmpeg_valid_color_transfers)
        self.color_transfer_widget.currentIndexChanged.connect(self.page_update)

        self.color_space_widget = QtWidgets.QComboBox()
        self.color_space_widget.addItem(t("Unspecified"))
        self.color_space_widget.addItems(ffmpeg_valid_color_space)
        self.color_space_widget.currentIndexChanged.connect(self.page_update)

        self.add_row_label(t("Color Formats"), self.last_row)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Primaries")), self.last_row, 1, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_primaries_widget, self.last_row, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Transfer")), self.last_row, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_transfer_widget, self.last_row, 4)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Space")), self.last_row, 5, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_space_widget, self.last_row, 6)

    def init_vbv(self):
        self.last_row += 1
        self.maxrate_widget = QtWidgets.QLineEdit()
        # self.maxrate_widget.setPlaceholderText("3000")
        self.maxrate_widget.setValidator(self.only_int)
        self.maxrate_widget.textChanged.connect(self.page_update)

        self.bufsize_widget = QtWidgets.QLineEdit()
        # self.bufsize_widget.setPlaceholderText("3000")
        self.bufsize_widget.setValidator(self.only_int)
        self.bufsize_widget.textChanged.connect(self.page_update)

        # self.vbv_checkbox = QtWidgets.QCheckBox(t("Enable VBV"))
        # self.vbv_checkbox.toggled.connect(self.vbv_check_changed)

        self.add_row_label(f'{t("Video Buffering")}\n{t("Verifier")} (VBV)', self.last_row)
        self.layout.addWidget(
            QtWidgets.QLabel(f'{t("Maxrate")} (kbps)'), self.last_row, 1, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.maxrate_widget, self.last_row, 2)
        self.layout.addWidget(
            QtWidgets.QLabel(f'{t("Bufsize")} (kbps)'), self.last_row, 3, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.bufsize_widget, self.last_row, 4)
        self.layout.addWidget(QtWidgets.QLabel("Both must have values to be enabled"), self.last_row, 5, 1, 2)

    # def vbv_check_changed(self):
    #     self.bufsize_widget.setEnabled(self.vbv_checkbox.isChecked())
    #     self.maxrate_widget.setEnabled(self.vbv_checkbox.isChecked())
    #     self.page_update()

    # def init_subtitle_overlay_fix(self):
    #     self.last_row += 1
    # TODO figure out overlay for subtitles move up
    # overlay=y=-140
    # crop=1904:800:6:140
    # (800 + 140) - 1080 == -140

    def init_hw_message(self):
        self.last_row += 1
        label = QtWidgets.QLabel("ʘ " + t("Not supported by rigaya's hardware encoders"))
        if self.app.fastflix.config.theme == "onyx":
            label.setStyleSheet("color: #b5b5b5")

        self.layout.addWidget(label, self.last_row, 0, 1, 2)

    def init_titles(self):
        self.video_title = QtWidgets.QLineEdit()
        self.video_title.setPlaceholderText(t("Video Title"))
        self.video_title.textChanged.connect(self.page_update)

        self.video_track_title = QtWidgets.QLineEdit()
        self.video_track_title.setPlaceholderText(t("Video Track Title") + " ʘ")
        self.video_track_title.textChanged.connect(self.page_update)

        self.layout.addWidget(QtWidgets.QLabel(t("Video Title")), self.last_row, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.video_title, self.last_row, 4)
        self.layout.addWidget(
            QtWidgets.QLabel(t("Video Track Title") + " ʘ"), self.last_row, 5, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.video_track_title, self.last_row, 6)

    def init_custom_filters(self):
        self.last_row += 1

        self.first_filters = QtWidgets.QLineEdit()
        self.first_filters.textChanged.connect(self.page_update)

        self.second_filters = QtWidgets.QLineEdit()
        self.second_filters.textChanged.connect(self.page_update)

        self.add_row_label(t("Custom Filters"), self.last_row)
        self.layout.addWidget(QtWidgets.QLabel(t("First Pass")), self.last_row, 1, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.first_filters, self.last_row, 2, 1, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Second Pass")), self.last_row, 4, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.second_filters, self.last_row, 5, 1, 2)

    def update_settings(self):
        if self.updating or not self.app.fastflix.current_video:
            return False
        self.updating = True
        self.app.fastflix.current_video.video_settings.video_speed = video_speeds[self.video_speed_widget.currentText()]
        self.app.fastflix.current_video.video_settings.deblock = non(self.deblock_widget.currentText())
        self.app.fastflix.current_video.video_settings.deblock_size = int(self.deblock_size_widget.currentText())
        self.app.fastflix.current_video.video_settings.tone_map = self.tone_map_widget.currentText()
        self.app.fastflix.current_video.video_settings.vsync = non(self.vsync_widget.currentText())

        try:
            if self.brightness_widget.text().strip() != "":
                self.app.fastflix.current_video.video_settings.brightness = str(float(self.brightness_widget.text()))
        except ValueError:
            logger.warning("Invalid brightness value")

        try:
            if self.saturation_widget.text().strip() != "":
                self.app.fastflix.current_video.video_settings.saturation = str(float(self.saturation_widget.text()))
        except ValueError:
            logger.warning("Invalid saturation value")

        try:
            if self.contrast_widget.text().strip() != "":
                self.app.fastflix.current_video.video_settings.contrast = str(float(self.contrast_widget.text()))
        except ValueError:
            logger.warning("Invalid contrast value")

        # self.app.fastflix.current_video.video_settings.first_pass_filters = self.first_filters.text() or None
        # self.app.fastflix.current_video.video_settings.second_filters = self.second_filters.text() or None

        if not self.incoming_same_as_source.isChecked():
            self.app.fastflix.current_video.video_settings.source_fps = self.incoming_fps_widget.text()
        if not self.outgoing_same_as_source.isChecked():
            self.app.fastflix.current_video.video_settings.output_fps = self.outgoing_fps_widget.text()

        if self.denoise_type_widget.currentIndex() == 0:
            self.app.fastflix.current_video.video_settings.denoise = None
        else:
            self.app.fastflix.current_video.video_settings.denoise = denoise_presets[
                self.denoise_type_widget.currentText()
            ][self.denoise_strength_widget.currentText()]

        if self.color_primaries_widget.currentIndex() == 0:
            self.app.fastflix.current_video.video_settings.color_primaries = None
        else:
            self.app.fastflix.current_video.video_settings.color_primaries = self.color_primaries_widget.currentText()

        if self.color_transfer_widget.currentIndex() == 0:
            self.app.fastflix.current_video.video_settings.color_transfer = None
        else:
            self.app.fastflix.current_video.video_settings.color_transfer = self.color_transfer_widget.currentText()

        if self.color_space_widget.currentIndex() == 0:
            self.app.fastflix.current_video.video_settings.color_space = None
        else:
            self.app.fastflix.current_video.video_settings.color_space = self.color_space_widget.currentText()

        if self.maxrate_widget.text() and self.bufsize_widget.text():
            self.app.fastflix.current_video.video_settings.maxrate = int(self.maxrate_widget.text())
            self.app.fastflix.current_video.video_settings.bufsize = int(self.bufsize_widget.text())
        else:
            self.app.fastflix.current_video.video_settings.maxrate = None
            self.app.fastflix.current_video.video_settings.bufsize = None

        self.updating = False

    def get_settings(self):
        denoise = None
        if self.denoise_type_widget.currentIndex() != 0:
            denoise = denoise_presets[self.denoise_type_widget.currentText()][
                self.denoise_strength_widget.currentText()
            ]

        maxrate = None
        bufsize = None
        if self.maxrate_widget.text() and self.bufsize_widget.text():
            maxrate = int(self.maxrate_widget.text())
            bufsize = int(self.bufsize_widget.text())

        contrast = None
        if self.contrast_widget.text().strip() != "":
            try:
                contrast = str(float(self.contrast_widget.text()))
            except ValueError:
                logger.warning("Invalid contrast value")

        saturation = None
        if self.saturation_widget.text().strip() != "":
            try:
                saturation = str(float(self.saturation_widget.text()))
            except ValueError:
                logger.warning("Invalid saturation value")

        brightness = None
        if self.brightness_widget.text().strip() != "":
            try:
                brightness = str(float(self.brightness_widget.text()))
            except ValueError:
                logger.warning("Invalid brightness value")

        return AdvancedOptions(
            video_speed=video_speeds[self.video_speed_widget.currentText()],
            deblock=non(self.deblock_widget.currentText()),
            deblock_size=int(self.deblock_size_widget.currentText()),
            tone_map=self.tone_map_widget.currentText(),
            vsync=non(self.vsync_widget.currentText()),
            brightness=brightness,
            saturation=saturation,
            contrast=contrast,
            maxrate=maxrate,
            bufsize=bufsize,
            source_fps=(None if self.incoming_same_as_source.isChecked() else self.incoming_fps_widget.text()),
            output_fps=(None if self.outgoing_same_as_source.isChecked() else self.outgoing_fps_widget.text()),
            color_space=(
                None if self.color_space_widget.currentIndex() == 0 else self.color_space_widget.currentText()
            ),
            color_transfer=(
                None if self.color_transfer_widget.currentIndex() == 0 else self.color_transfer_widget.currentText()
            ),
            color_primaries=(
                None if self.color_primaries_widget.currentIndex() == 0 else self.color_primaries_widget.currentText()
            ),
            denoise=denoise,
            denoise_type_index=self.denoise_type_widget.currentIndex(),
            denoise_strength_index=self.denoise_strength_widget.currentIndex(),
            # first_pass_filters=self.first_filters.text() or None,
            # second_pass_filters=self.second_filters.text() or None,
        )

    def hdr_settings(self):
        if self.main.remove_hdr:
            self.color_primaries_widget.setCurrentText("bt709")
            if self.app.fastflix.current_video:
                self.app.fastflix.current_video.video_settings.color_primaries = "bt709"
                self.app.fastflix.current_video.video_settings.color_transfer = None
                self.app.fastflix.current_video.video_settings.color_space = None
            self.color_transfer_widget.setCurrentIndex(0)
            self.color_space_widget.setCurrentIndex(0)
        else:
            if self.app.fastflix.current_video:
                if color_space := self.app.fastflix.config.advanced_opt("color_space"):
                    self.color_space_widget.setCurrentText(color_space)
                elif self.app.fastflix.current_video.color_space:
                    self.color_space_widget.setCurrentText(self.app.fastflix.current_video.color_space)
                else:
                    self.color_space_widget.setCurrentIndex(0)

                if color_transfer := self.app.fastflix.config.advanced_opt("color_transfer"):
                    self.color_transfer_widget.setCurrentText(color_transfer)
                elif self.app.fastflix.current_video.color_transfer:
                    self.color_transfer_widget.setCurrentText(self.app.fastflix.current_video.color_transfer)
                else:
                    self.color_transfer_widget.setCurrentIndex(0)

                if color_primaries := self.app.fastflix.config.advanced_opt("color_primaries"):
                    self.color_primaries_widget.setCurrentText(color_primaries)
                elif self.app.fastflix.current_video.color_primaries:
                    self.color_primaries_widget.setCurrentText(self.app.fastflix.current_video.color_primaries)
                else:
                    self.color_primaries_widget.setCurrentIndex(0)
            else:
                if color_space := self.app.fastflix.config.advanced_opt("color_space"):
                    self.color_space_widget.setCurrentText(color_space)
                else:
                    self.color_space_widget.setCurrentIndex(0)
                if color_transfer := self.app.fastflix.config.advanced_opt("color_transfer"):
                    self.color_transfer_widget.setCurrentText(color_transfer)
                else:
                    self.color_transfer_widget.setCurrentIndex(0)
                if color_primaries := self.app.fastflix.config.advanced_opt("color_primaries"):
                    self.color_primaries_widget.setCurrentText(color_primaries)
                else:
                    self.color_primaries_widget.setCurrentIndex(0)

    def page_update(self, build_thumbnail=False):
        self.main.page_update(build_thumbnail=build_thumbnail)

    def reset(self, settings: VideoSettings = None):
        if settings:
            self.video_speed_widget.setCurrentText(get_key(video_speeds, settings.video_speed))
            self.brightness_widget.setText(settings.brightness or "")
            self.saturation_widget.setText(settings.saturation or "")
            self.contrast_widget.setText(settings.contrast or "")

            if settings.deblock:
                self.deblock_widget.setCurrentText(settings.deblock)
            self.deblock_size_widget.setCurrentText(str(settings.deblock_size))
            self.tone_map_widget.setCurrentText(settings.tone_map)

            if not settings.source_fps:
                self.incoming_same_as_source.setChecked(True)
                self.incoming_fps_widget.setText("")
            else:
                self.incoming_same_as_source.setChecked(False)
                self.incoming_fps_widget.setText(settings.source_fps)

            if not settings.output_fps:
                self.outgoing_same_as_source.setChecked(True)
                self.outgoing_fps_widget.setText("")
            else:
                self.outgoing_same_as_source.setChecked(False)
                self.outgoing_fps_widget.setText(settings.output_fps)

            if settings.denoise:
                for denoise_type, preset in denoise_presets.items():
                    for preset_name, value in preset.items():
                        if settings.denoise == value:
                            self.denoise_type_widget.setCurrentText(denoise_type)
                            self.denoise_strength_widget.setCurrentText(preset_name)
            if settings.vsync:
                self.vsync_widget.setCurrentText(settings.vsync)
            else:
                self.vsync_widget.setCurrentIndex(0)

            if settings.maxrate:
                self.maxrate_widget.setText(str(settings.maxrate))
                self.bufsize_widget.setText(str(settings.bufsize))
            else:
                self.maxrate_widget.setText("")
                self.bufsize_widget.setText("")

            if settings.color_space:
                self.color_space_widget.setCurrentText(settings.color_space)
            else:
                self.color_space_widget.setCurrentIndex(0)

            if settings.color_transfer:
                self.color_transfer_widget.setCurrentText(settings.color_transfer)
            else:
                self.color_transfer_widget.setCurrentIndex(0)

            if settings.color_primaries:
                self.color_primaries_widget.setCurrentText(settings.color_primaries)
            else:
                self.color_primaries_widget.setCurrentIndex(0)

            if settings.video_title:
                self.video_title.setText(settings.video_title)

            if settings.video_track_title:
                self.video_track_title.setText(settings.video_track_title)

        else:
            self.video_speed_widget.setCurrentIndex(
                list(video_speeds.values()).index(self.app.fastflix.config.advanced_opt("video_speed"))
            )

            deblock = self.app.fastflix.config.advanced_opt("deblock")
            if not deblock:
                self.deblock_widget.setCurrentIndex(0)
            else:
                self.deblock_widget.setCurrentText(deblock)
            self.deblock_size_widget.setCurrentText(str(self.app.fastflix.config.advanced_opt("deblock_size")))
            tone_map_select = self.app.fastflix.config.advanced_opt("tone_map")

            self.tone_map_widget.setCurrentIndex(tone_map_items.index(tone_map_select) if tone_map_select else 0)

            # FPS
            source_fps = self.app.fastflix.config.advanced_opt("source_fps")
            output_fps = self.app.fastflix.config.advanced_opt("output_fps")
            self.incoming_same_as_source.setChecked(True if not source_fps else False)
            self.outgoing_same_as_source.setChecked(True if not output_fps else False)
            self.incoming_fps_widget.setDisabled(True if not source_fps else False)
            self.outgoing_fps_widget.setDisabled(True if not output_fps else False)
            self.incoming_fps_widget.setText("" if not source_fps else source_fps)
            self.outgoing_fps_widget.setText("" if not output_fps else output_fps)

            self.denoise_type_widget.setCurrentIndex(self.app.fastflix.config.advanced_opt("denoise_type_index"))
            self.denoise_strength_widget.setCurrentIndex(
                self.app.fastflix.config.advanced_opt("denoise_strength_index")
            )

            vsync_value = self.app.fastflix.config.advanced_opt("vsync")
            self.vsync_widget.setCurrentIndex(0 if not vsync_value else (vsync.index(vsync_value) + 1))

            # VBV
            maxrate = self.app.fastflix.config.advanced_opt("maxrate")
            bufsize = self.app.fastflix.config.advanced_opt("bufsize")
            vbv = bool(maxrate and bufsize)
            self.maxrate_widget.setText(str(maxrate) if maxrate and vbv else "")
            self.bufsize_widget.setText(str(bufsize) if maxrate and vbv else "")

            # Equalizer
            self.brightness_widget.setText(self.app.fastflix.config.advanced_opt("brightness") or "")
            self.saturation_widget.setText(self.app.fastflix.config.advanced_opt("saturation") or "")
            self.contrast_widget.setText(self.app.fastflix.config.advanced_opt("contrast") or "")

            self.hdr_settings()
            # self.video_title.setText("")
            # self.video_track_title.setText("")

        # Set the frame rate
        if self.app.fastflix.current_video:
            dont_set = False
            frame_rate_type = (
                t("Constant")
                if self.app.fastflix.current_video.frame_rate == self.app.fastflix.current_video.average_frame_rate
                else t("Variable")
            )
            if "/" in self.app.fastflix.current_video.frame_rate:
                try:
                    over, under = self.app.fastflix.current_video.frame_rate.split("/")
                    if under == "1":
                        self.source_frame_rate.setText(f"{over}     ( {frame_rate_type} )")
                        dont_set = True
                    readable_rate = int(over) / int(under)
                except Exception:
                    self.source_frame_rate.setText(
                        f"{self.app.fastflix.current_video.frame_rate}      ( {frame_rate_type} )"
                    )
                else:
                    if not dont_set:
                        self.source_frame_rate.setText(
                            f"{self.app.fastflix.current_video.frame_rate}   [ ~{readable_rate:.3f} ]      ( {frame_rate_type} )"
                        )
            else:
                self.source_frame_rate.setText(
                    f"{self.app.fastflix.current_video.frame_rate}     ( {frame_rate_type} )"
                )
        else:
            self.source_frame_rate.setText("")

    def new_source(self):
        self.reset()

        advanced_options: AdvancedOptions = self.app.fastflix.config.opt("advanced_options")

        if color_primaries := advanced_options.color_primaries:
            self.color_primaries_widget.setCurrentText(color_primaries)
        elif self.app.fastflix.current_video.color_primaries in ffmpeg_valid_color_primaries:
            self.color_primaries_widget.setCurrentIndex(
                ffmpeg_valid_color_primaries.index(self.app.fastflix.current_video.color_primaries) + 1
            )
        else:
            self.color_primaries_widget.setCurrentIndex(0)

        if color_transfer := advanced_options.color_transfer:
            self.color_transfer_widget.setCurrentText(color_transfer)
        elif self.app.fastflix.current_video.color_transfer in ffmpeg_valid_color_transfers:
            self.color_transfer_widget.setCurrentIndex(
                ffmpeg_valid_color_transfers.index(self.app.fastflix.current_video.color_transfer) + 1
            )
        else:
            self.color_transfer_widget.setCurrentIndex(0)

        if color_space := advanced_options.color_space:
            self.color_space_widget.setCurrentText(color_space)
        elif self.app.fastflix.current_video.color_space in ffmpeg_valid_color_space:
            self.color_space_widget.setCurrentIndex(
                ffmpeg_valid_color_space.index(self.app.fastflix.current_video.color_space) + 1
            )
        else:
            self.color_space_widget.setCurrentIndex(0)

        if video_speed := advanced_options.video_speed:
            self.video_speed_widget.setCurrentText(get_key(video_speeds, video_speed))

        if deblock := advanced_options.deblock:
            self.deblock_widget.setCurrentText(deblock)

        if deblock_size := advanced_options.deblock_size:
            self.deblock_size_widget.setCurrentText(str(deblock_size))

        if tone_map := advanced_options.tone_map:
            self.tone_map_widget.setCurrentText(tone_map)

        if vsync := advanced_options.vsync:
            self.vsync_widget.setCurrentText(vsync)

        if brightness := advanced_options.brightness:
            self.brightness_widget.setText(brightness)

        if saturation := advanced_options.saturation:
            self.saturation_widget.setText(saturation)

        if contrast := advanced_options.contrast:
            self.contrast_widget.setText(contrast)

        if maxrate := advanced_options.maxrate:
            self.maxrate_widget.setText(str(maxrate))

        if bufsize := advanced_options.bufsize:
            self.bufsize_widget.setText(str(bufsize))

        if source_fps := advanced_options.source_fps:
            self.incoming_fps_widget.setText(source_fps)
            self.incoming_same_as_source.setChecked(False)
        else:
            self.incoming_same_as_source.setChecked(True)

        if output_fps := advanced_options.output_fps:
            self.outgoing_fps_widget.setText(output_fps)
            self.outgoing_same_as_source.setChecked(False)
        else:
            self.outgoing_same_as_source.setChecked(True)

        if denoise_type_index := advanced_options.denoise_type_index:
            self.denoise_type_widget.setCurrentIndex(denoise_type_index)
        if denoise_strength_index := advanced_options.denoise_strength_index:
            self.denoise_strength_widget.setCurrentIndex(denoise_strength_index)
