#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import VideoSettings
from fastflix.models.profiles import AdvancedOptions
from fastflix.widgets.toggle_switch import ToggleSwitch
from fastflix.ui_styles import get_onyx_label_style
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

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        container = QtWidgets.QWidget()
        container.setMinimumHeight(670)
        self.inner_layout = QtWidgets.QVBoxLayout(container)
        self.inner_layout.setSpacing(6)

        self.inner_layout.addWidget(self.init_video_details_group())
        self.inner_layout.addWidget(self.init_fps_group())
        self.inner_layout.addWidget(self.init_video_processing_group())
        self.inner_layout.addWidget(self.init_color_group())
        self.inner_layout.addWidget(self.init_output_group())
        self.inner_layout.addStretch()
        self.init_hw_message()

        scroll.setWidget(container)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(scroll)
        self.setLayout(self.layout)

    @staticmethod
    def setup_grid(gl, cols=6):
        for i in range(cols):
            gl.setColumnMinimumWidth(i, 120)
            gl.setColumnStretch(i, 1)

    @staticmethod
    def setup_group(group, rows):
        group.setMinimumHeight(rows * 40 + 30)
        group.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

    def init_video_details_group(self):
        group = QtWidgets.QGroupBox(t("Video Details"))
        gl = QtWidgets.QGridLayout(group)
        self.setup_grid(gl)

        self.video_title = QtWidgets.QLineEdit()
        self.video_title.setPlaceholderText(t("Video Title"))
        self.video_title.textChanged.connect(self.page_update)

        self.video_track_title = QtWidgets.QLineEdit()
        self.video_track_title.setPlaceholderText(t("Video Track Title"))
        self.video_track_title.textChanged.connect(self.page_update)

        gl.addWidget(QtWidgets.QLabel(t("Video Title")), 0, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.video_title, 0, 1)
        gl.addWidget(QtWidgets.QLabel(t("Video Track Title")), 0, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.video_track_title, 0, 3)

        self.setup_group(group, rows=1)
        return group

    def init_fps_group(self):
        group = QtWidgets.QGroupBox(t("Frame Rate"))
        gl = QtWidgets.QGridLayout(group)
        self.setup_grid(gl)

        self.incoming_fps_widget = QtWidgets.QLineEdit()
        self.incoming_fps_widget.setDisabled(True)
        self.incoming_fps_widget.textChanged.connect(self.page_update)
        self.outgoing_fps_widget = QtWidgets.QLineEdit()
        self.outgoing_fps_widget.setDisabled(True)
        self.outgoing_fps_widget.textChanged.connect(self.page_update)
        self.incoming_same_as_source = ToggleSwitch(t("Same as Source"))
        self.incoming_same_as_source.setChecked(True)
        self.incoming_same_as_source.toggled.connect(
            lambda: self.fps_update(self.incoming_same_as_source, self.incoming_fps_widget)
        )
        self.outgoing_same_as_source = ToggleSwitch(t("Same as Source"))
        self.outgoing_same_as_source.setChecked(True)
        self.outgoing_same_as_source.toggled.connect(
            lambda: self.fps_update(self.outgoing_same_as_source, self.outgoing_fps_widget)
        )

        self.source_frame_rate = QtWidgets.QLabel("")
        self.vsync_widget = QtWidgets.QComboBox()
        self.vsync_widget.addItem(t("Unspecified"))
        self.vsync_widget.addItems(vsync)
        self.vsync_widget.currentIndexChanged.connect(self.page_update)

        gl.addWidget(QtWidgets.QLabel(t("Override Source FPS")), 0, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.incoming_fps_widget, 0, 1)
        gl.addWidget(self.incoming_same_as_source, 0, 2)
        gl.addWidget(QtWidgets.QLabel(t("Source Frame Rate")), 0, 4, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.source_frame_rate, 0, 5)

        gl.addWidget(QtWidgets.QLabel(t("Output FPS")), 1, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.outgoing_fps_widget, 1, 1)
        gl.addWidget(self.outgoing_same_as_source, 1, 2)
        gl.addWidget(QtWidgets.QLabel(t("vsync")), 1, 4, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.vsync_widget, 1, 5)

        self.setup_group(group, rows=2)
        return group

    def init_video_processing_group(self):
        group = QtWidgets.QGroupBox(t("Video Processing"))
        gl = QtWidgets.QGridLayout(group)
        self.setup_grid(gl)
        row = 0

        # --- Video Speed / HDR row ---
        self.video_speed_widget = QtWidgets.QComboBox()
        self.video_speed_widget.addItems(video_speeds.keys())
        self.video_speed_widget.currentIndexChanged.connect(self.on_video_speed_changed)
        gl.addWidget(QtWidgets.QLabel(t("Video Speed") + " ʘ"), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.video_speed_widget, row, 1)

        self.reverse_video_widget = ToggleSwitch(t("Reverse Video") + " ʘ")
        self.reverse_video_widget.stateChanged.connect(self.on_reverse_video_changed)
        gl.addWidget(self.reverse_video_widget, row, 3)

        self.tone_map_widget = QtWidgets.QComboBox()
        self.tone_map_widget.addItems(tone_map_items)
        self.tone_map_widget.setCurrentIndex(5)
        self.tone_map_widget.currentIndexChanged.connect(self.page_update)
        gl.addWidget(QtWidgets.QLabel(t("HDR -> SDR Tone Map")), row, 4, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.tone_map_widget, row, 5)

        # --- Equalizer row 1: Brightness / Contrast / Saturation ---
        row += 1
        c_locale = QtCore.QLocale.c()

        self.brightness_widget = QtWidgets.QLineEdit()
        brightness_validator = QtGui.QDoubleValidator()
        brightness_validator.setLocale(c_locale)
        self.brightness_widget.setValidator(brightness_validator)
        self.brightness_widget.setToolTip("Default is: 0")

        self.brightness_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.contrast_widget = QtWidgets.QLineEdit()
        contrast_validator = QtGui.QDoubleValidator()
        contrast_validator.setLocale(c_locale)
        self.contrast_widget.setValidator(contrast_validator)
        self.contrast_widget.setToolTip("Default is: 1")

        self.contrast_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.saturation_widget = QtWidgets.QLineEdit()
        saturation_validator = QtGui.QDoubleValidator()
        saturation_validator.setLocale(c_locale)
        self.saturation_widget.setValidator(saturation_validator)
        self.saturation_widget.setToolTip("Default is: 1")

        self.saturation_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        gl.addWidget(QtWidgets.QLabel(t("Brightness")), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.brightness_widget, row, 1)
        gl.addWidget(QtWidgets.QLabel(t("Contrast")), row, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.contrast_widget, row, 3)
        gl.addWidget(QtWidgets.QLabel(t("Saturation")), row, 4, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.saturation_widget, row, 5)

        # --- Equalizer row 2: Gamma / Hue ---
        row += 1

        self.gamma_widget = QtWidgets.QLineEdit()
        gamma_validator = QtGui.QDoubleValidator(0.1, 10.0, 2)
        gamma_validator.setLocale(c_locale)
        self.gamma_widget.setValidator(gamma_validator)
        self.gamma_widget.setToolTip("Default is: 1 (range: 0.1 - 10.0)")

        self.gamma_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        self.hue_widget = QtWidgets.QLineEdit()
        hue_validator = QtGui.QDoubleValidator(-180.0, 180.0, 2)
        hue_validator.setLocale(c_locale)
        self.hue_widget.setValidator(hue_validator)
        self.hue_widget.setToolTip("Default is: 0 (range: -180 - 180 degrees)")

        self.hue_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        gl.addWidget(QtWidgets.QLabel(t("Gamma")), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.gamma_widget, row, 1)
        gl.addWidget(QtWidgets.QLabel(t("Hue")), row, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.hue_widget, row, 3)

        # --- Denoise row ---
        row += 1

        self.denoise_type_widget = QtWidgets.QComboBox()
        self.denoise_type_widget.addItems(["none", "nlmeans", "atadenoise", "hqdn3d", "vaguedenoiser"])
        self.denoise_type_widget.setCurrentIndex(0)
        self.denoise_type_widget.currentIndexChanged.connect(self.page_update)

        self.denoise_strength_widget = QtWidgets.QComboBox()
        self.denoise_strength_widget.addItems(["weak", "moderate", "strong"])
        self.denoise_strength_widget.setCurrentIndex(0)
        self.denoise_strength_widget.currentIndexChanged.connect(self.page_update)

        gl.addWidget(QtWidgets.QLabel(t("Denoise")), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.denoise_type_widget, row, 1)
        gl.addWidget(QtWidgets.QLabel(t("Strength")), row, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.denoise_strength_widget, row, 3)

        # --- Deblock row ---
        row += 1

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

        gl.addWidget(QtWidgets.QLabel(t("Deblock")), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.deblock_widget, row, 1)
        gl.addWidget(QtWidgets.QLabel(t("Block Size")), row, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.deblock_size_widget, row, 3)

        # --- Sharpen / GOP Length row ---
        row += 1

        self.sharpen_widget = QtWidgets.QLineEdit()
        sharpen_validator = QtGui.QDoubleValidator(0.0, 1.0, 2)
        sharpen_validator.setLocale(c_locale)
        self.sharpen_widget.setValidator(sharpen_validator)
        self.sharpen_widget.setToolTip("Default is: 0 (range: 0.0 - 1.0)")
        self.sharpen_widget.textChanged.connect(lambda: self.page_update(build_thumbnail=True))

        gl.addWidget(QtWidgets.QLabel(t("Sharpen")), row, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.sharpen_widget, row, 1)

        self.gop_length_widget = QtWidgets.QLineEdit()
        self.gop_length_widget.setValidator(QtGui.QIntValidator(0, 9999))
        self.gop_length_widget.setToolTip(t("GOP length in frames (leave empty for encoder default)"))
        self.gop_length_widget.textChanged.connect(self.page_update)

        gl.addWidget(QtWidgets.QLabel(t("GOP Length")), row, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.gop_length_widget, row, 3)

        self.setup_group(group, rows=6)
        return group

    def init_color_group(self):
        group = QtWidgets.QGroupBox(t("Color"))
        gl = QtWidgets.QGridLayout(group)
        self.setup_grid(gl)

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

        gl.addWidget(QtWidgets.QLabel(t("Color Primaries")), 0, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.color_primaries_widget, 0, 1)
        gl.addWidget(QtWidgets.QLabel(t("Color Transfer")), 0, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.color_transfer_widget, 0, 3)
        gl.addWidget(QtWidgets.QLabel(t("Color Space")), 0, 4, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.color_space_widget, 0, 5)

        self.setup_group(group, rows=1)
        return group

    def init_output_group(self):
        group = QtWidgets.QGroupBox(t("Output"))
        gl = QtWidgets.QGridLayout(group)
        self.setup_grid(gl)

        self.maxrate_widget = QtWidgets.QLineEdit()
        self.maxrate_widget.setValidator(self.only_int)
        self.maxrate_widget.textChanged.connect(self.page_update)

        self.bufsize_widget = QtWidgets.QLineEdit()
        self.bufsize_widget.setValidator(self.only_int)
        self.bufsize_widget.textChanged.connect(self.page_update)

        gl.addWidget(QtWidgets.QLabel(f"{t('Maxrate')} (kbps)"), 0, 0, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.maxrate_widget, 0, 1)
        gl.addWidget(QtWidgets.QLabel(f"{t('Bufsize')} (kbps)"), 0, 2, alignment=QtCore.Qt.AlignRight)
        gl.addWidget(self.bufsize_widget, 0, 3)
        gl.addWidget(QtWidgets.QLabel(t("Both must have values to be enabled")), 0, 4, 1, 2)

        self.faststart_widget = ToggleSwitch(t("Fast Start (MP4/MOV)"))
        self.faststart_widget.setChecked(True)
        self.faststart_widget.setToolTip(t("Moves metadata to the beginning of the file for faster streaming start"))
        self.faststart_widget.stateChanged.connect(self.page_update)
        self.faststart_widget.setVisible(False)
        gl.addWidget(self.faststart_widget, 1, 0, 1, 2)

        self.setup_group(group, rows=2)
        return group

    def init_hw_message(self):
        label = QtWidgets.QLabel("ʘ " + t("Not supported by rigaya's hardware encoders (Video Speed, Reverse Video)"))
        if self.app.fastflix.config.theme == "onyx":
            label.setStyleSheet(get_onyx_label_style(muted=True))
        self.inner_layout.addWidget(label)

    def fps_update(self, myself, widget):
        widget.setDisabled(myself.isChecked())
        self.page_update()

    def on_video_speed_changed(self):
        if not self.app.fastflix.config.suppress_video_speed_warning:
            current_speed = video_speeds[self.video_speed_widget.currentText()]
            if current_speed != 1:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle(t("Video Speed Warning"))
                msg.setText(t("Warning: Audio will not be modified when changing video speed."))
                cb = QtWidgets.QCheckBox(t("Don't show this warning again"))
                msg.setCheckBox(cb)
                msg.addButton(t("OK"), QtWidgets.QMessageBox.AcceptRole)
                msg.exec()
                if cb.isChecked():
                    self.app.fastflix.config.suppress_video_speed_warning = True
                    self.app.fastflix.config.save()
        self.page_update()

    def on_reverse_video_changed(self):
        if self.reverse_video_widget.isChecked() and not self.app.fastflix.config.suppress_reverse_video_warning:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(t("Reverse Video Warning"))
            msg.setText(
                t("The reverse filter buffers all video frames in memory.")
                + " "
                + t("This may require significant RAM for long or high-resolution videos.")
                + "\n\n"
                + t("Audio on converted (non-copy) tracks will also be reversed.")
            )
            cb = QtWidgets.QCheckBox(t("Don't show this warning again"))
            msg.setCheckBox(cb)
            msg.addButton(t("OK"), QtWidgets.QMessageBox.AcceptRole)
            msg.exec()
            if cb.isChecked():
                self.app.fastflix.config.suppress_reverse_video_warning = True
                self.app.fastflix.config.save()
        self.page_update()

    def update_settings(self):
        if self.updating or not self.app.fastflix.current_video:
            return False
        self.updating = True
        self.app.fastflix.current_video.video_settings.video_speed = video_speeds[self.video_speed_widget.currentText()]
        self.app.fastflix.current_video.video_settings.reverse_video = self.reverse_video_widget.isChecked()
        self.app.fastflix.current_video.video_settings.deblock = non(self.deblock_widget.currentText())
        self.app.fastflix.current_video.video_settings.deblock_size = int(self.deblock_size_widget.currentText())
        self.app.fastflix.current_video.video_settings.tone_map = self.tone_map_widget.currentText()
        self.app.fastflix.current_video.video_settings.vsync = non(self.vsync_widget.currentText())

        if self.brightness_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.brightness = str(float(self.brightness_widget.text()))
            except ValueError:
                logger.warning("Invalid brightness value")
        else:
            self.app.fastflix.current_video.video_settings.brightness = None

        if self.saturation_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.saturation = str(float(self.saturation_widget.text()))
            except ValueError:
                logger.warning("Invalid saturation value")
        else:
            self.app.fastflix.current_video.video_settings.saturation = None

        if self.contrast_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.contrast = str(float(self.contrast_widget.text()))
            except ValueError:
                logger.warning("Invalid contrast value")
        else:
            self.app.fastflix.current_video.video_settings.contrast = None

        if self.gamma_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.gamma = str(float(self.gamma_widget.text()))
            except ValueError:
                logger.warning("Invalid gamma value")
        else:
            self.app.fastflix.current_video.video_settings.gamma = None

        if self.hue_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.hue = str(float(self.hue_widget.text()))
            except ValueError:
                logger.warning("Invalid hue value")
        else:
            self.app.fastflix.current_video.video_settings.hue = None

        if self.sharpen_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.sharpen = str(float(self.sharpen_widget.text()))
            except ValueError:
                logger.warning("Invalid sharpen value")
        else:
            self.app.fastflix.current_video.video_settings.sharpen = None

        self.app.fastflix.current_video.video_settings.faststart = self.faststart_widget.isChecked()

        if self.gop_length_widget.text().strip():
            try:
                self.app.fastflix.current_video.video_settings.gop_length = int(self.gop_length_widget.text())
            except ValueError:
                logger.warning("Invalid GOP length value")
        else:
            self.app.fastflix.current_video.video_settings.gop_length = None

        # self.app.fastflix.current_video.video_settings.first_pass_filters = self.first_filters.text() or None
        # self.app.fastflix.current_video.video_settings.second_filters = self.second_filters.text() or None

        if not self.incoming_same_as_source.isChecked():
            self.app.fastflix.current_video.video_settings.source_fps = self.incoming_fps_widget.text()
        else:
            self.app.fastflix.current_video.video_settings.source_fps = None
        if not self.outgoing_same_as_source.isChecked():
            self.app.fastflix.current_video.video_settings.output_fps = self.outgoing_fps_widget.text()
        else:
            self.app.fastflix.current_video.video_settings.output_fps = None

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

        self.update_faststart_visibility()
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

        gamma = None
        if self.gamma_widget.text().strip() != "":
            try:
                gamma = str(float(self.gamma_widget.text()))
            except ValueError:
                logger.warning("Invalid gamma value")

        hue = None
        if self.hue_widget.text().strip() != "":
            try:
                hue = str(float(self.hue_widget.text()))
            except ValueError:
                logger.warning("Invalid hue value")

        sharpen = None
        if self.sharpen_widget.text().strip() != "":
            try:
                sharpen = str(float(self.sharpen_widget.text()))
            except ValueError:
                logger.warning("Invalid sharpen value")

        gop_length = None
        if self.gop_length_widget.text().strip():
            try:
                gop_length = int(self.gop_length_widget.text())
            except ValueError:
                logger.warning("Invalid GOP length value")

        return AdvancedOptions(
            video_speed=video_speeds[self.video_speed_widget.currentText()],
            reverse_video=self.reverse_video_widget.isChecked(),
            deblock=non(self.deblock_widget.currentText()),
            deblock_size=int(self.deblock_size_widget.currentText()),
            tone_map=self.tone_map_widget.currentText(),
            vsync=non(self.vsync_widget.currentText()),
            brightness=brightness,
            saturation=saturation,
            contrast=contrast,
            gamma=gamma,
            hue=hue,
            sharpen=sharpen,
            faststart=self.faststart_widget.isChecked(),
            deinterlace=self.main.widgets.deinterlace.isChecked(),
            gop_length=gop_length,
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
        self.update_faststart_visibility()
        self.main.page_update(build_thumbnail=build_thumbnail)

    def update_faststart_visibility(self):
        if not hasattr(self, "faststart_widget"):
            return
        ext = ""
        # Check the output type combo first (always reflects current selection)
        if hasattr(self.main, "widgets") and hasattr(self.main.widgets, "output_type_combo"):
            ext = self.main.widgets.output_type_combo.currentText().lower()
        # Fall back to output_path if available
        elif self.app.fastflix.current_video and self.app.fastflix.current_video.video_settings.output_path:
            ext = self.app.fastflix.current_video.video_settings.output_path.suffix.lower()
        self.faststart_widget.setVisible(ext in (".mp4", ".mov", ".m4v"))

    def reset(self, settings: VideoSettings = None):
        if settings:
            self.video_speed_widget.setCurrentText(get_key(video_speeds, settings.video_speed))
            self.reverse_video_widget.setChecked(settings.reverse_video)
            self.brightness_widget.setText(settings.brightness or "")
            self.saturation_widget.setText(settings.saturation or "")
            self.contrast_widget.setText(settings.contrast or "")
            self.gamma_widget.setText(settings.gamma or "")
            self.hue_widget.setText(settings.hue or "")
            self.sharpen_widget.setText(settings.sharpen or "")
            self.gop_length_widget.setText(str(settings.gop_length) if settings.gop_length else "")
            self.faststart_widget.setChecked(settings.faststart if hasattr(settings, "faststart") else True)

            if settings.deblock:
                self.deblock_widget.setCurrentText(settings.deblock)
            else:
                self.deblock_widget.setCurrentIndex(0)
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
            else:
                self.denoise_type_widget.setCurrentIndex(0)
                self.denoise_strength_widget.setCurrentIndex(0)
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
            else:
                self.video_title.setText("")

            if settings.video_track_title:
                self.video_track_title.setText(settings.video_track_title)
            else:
                self.video_track_title.setText("")

        else:
            self.video_speed_widget.setCurrentIndex(
                list(video_speeds.values()).index(self.app.fastflix.config.advanced_opt("video_speed"))
            )
            self.reverse_video_widget.setChecked(self.app.fastflix.config.advanced_opt("reverse_video"))

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
            self.gamma_widget.setText(self.app.fastflix.config.advanced_opt("gamma") or "")
            self.hue_widget.setText(self.app.fastflix.config.advanced_opt("hue") or "")
            self.sharpen_widget.setText(self.app.fastflix.config.advanced_opt("sharpen") or "")
            gop_val = self.app.fastflix.config.advanced_opt("gop_length")
            self.gop_length_widget.setText(str(gop_val) if gop_val else "")
            faststart_val = self.app.fastflix.config.advanced_opt("faststart")
            self.faststart_widget.setChecked(faststart_val if faststart_val is not None else True)

            self.hdr_settings()
            self.video_title.setText("")
            self.video_track_title.setText("")

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

        self.reverse_video_widget.setChecked(advanced_options.reverse_video)

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

        if gamma := advanced_options.gamma:
            self.gamma_widget.setText(gamma)

        if hue := advanced_options.hue:
            self.hue_widget.setText(hue)

        if sharpen := advanced_options.sharpen:
            self.sharpen_widget.setText(sharpen)

        if gop_length := advanced_options.gop_length:
            self.gop_length_widget.setText(str(gop_length))

        self.faststart_widget.setChecked(advanced_options.faststart)

        self.main.widgets.deinterlace.setChecked(advanced_options.deinterlace)

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

        denoise_type_index = advanced_options.denoise_type_index
        if denoise_type_index is not None:
            self.denoise_type_widget.setCurrentIndex(denoise_type_index)
        denoise_strength_index = advanced_options.denoise_strength_index
        if denoise_strength_index is not None:
            self.denoise_strength_widget.setCurrentIndex(denoise_strength_index)
