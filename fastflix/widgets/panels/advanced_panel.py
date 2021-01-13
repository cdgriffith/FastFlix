#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import VideoSettings
from fastflix.resources import warning_icon

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

ffmpeg_valid_color_primaries = [
    "bt709",
    "bt470m",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "film",
    "bt2020",
    "smpte428",
    "smpte428_1",
    "smpte431",
    "smpte432",
    "jedec-p22",
]

ffmpeg_valid_color_transfers = [
    "bt709",
    "gamma22",
    "gamma28",
    "smpte170m",
    "smpte240m",
    "linear",
    "log",
    "log100",
    "log_sqrt",
    "log316",
    "iec61966_2_4",
    "iec61966-2-4",
    "bt1361",
    "bt1361e",
    "iec61966_2_1",
    "iec61966-2-1",
    "bt2020_10",
    "bt2020_10bit",
    "bt2020_12",
    "bt2020_12bit",
    "smpte2084",
    "smpte428",
    "smpte428_1",
    "arib-std-b67",
]

ffmpeg_valid_color_space = [
    "rgb",
    "bt709",
    "fcc",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "ycocg",
    "bt2020nc",
    "bt2020_ncl",
    "bt2020c",
    "bt2020_cl",
    "smpte2085",
    "chroma-derived-nc",
    "chroma-derived-c",
    "ictcp",
]

vsync = ["auto", "passthrough", "cfr", "vfr", "drop"]


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
        self.init_tone_map()
        self.add_spacer()
        self.init_denoise()
        self.add_spacer()
        self.init_deblock()
        self.add_spacer()
        self.init_color_info()
        self.add_spacer()
        self.init_vbv()

        self.last_row += 1

        self.layout.setRowStretch(self.last_row, True)
        self.layout.setColumnStretch(8, True)
        self.last_row += 1

        warning_label = QtWidgets.QLabel()
        icon = QtGui.QIcon(warning_icon)
        warning_label.setPixmap(icon.pixmap(22))

        self.layout.addWidget(warning_label, self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(
            QtWidgets.QLabel(t("Advanced settings are currently not saved in Profiles")), self.last_row, 1, 1, 4
        )
        for i in range(7):
            self.layout.setColumnMinimumWidth(i, 155)
        self.setLayout(self.layout)

    def add_spacer(self):
        self.last_row += 1
        spacer_widget = QtWidgets.QWidget(self)
        spacer_widget.setFixedHeight(1)
        spacer_widget.setStyleSheet("background-color: #ddd")
        self.layout.addWidget(spacer_widget, self.last_row, 0, 1, 8)

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
        self.source_frame_rate_type = QtWidgets.QLabel("")
        self.vsync_widget = QtWidgets.QComboBox()
        self.vsync_widget.addItem(t("Unspecified"))
        self.vsync_widget.addItems(vsync)
        self.vsync_widget.currentIndexChanged.connect(self.page_update)

        self.layout.addWidget(
            QtWidgets.QLabel(t("Override Source FPS")), self.last_row, 0, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.incoming_fps_widget, self.last_row, 1)
        self.layout.addWidget(self.incoming_same_as_source, self.last_row, 2)
        self.layout.addWidget(
            QtWidgets.QLabel(t("Source Frame Rate")), self.last_row, 4, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.source_frame_rate, self.last_row, 5)
        self.layout.addWidget(self.source_frame_rate_type, self.last_row, 6)

        self.last_row += 1
        self.layout.addWidget(QtWidgets.QLabel(t("Output FPS")), self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.outgoing_fps_widget, self.last_row, 1)
        self.layout.addWidget(self.outgoing_same_as_source, self.last_row, 2)

        self.layout.addWidget(QtWidgets.QLabel(t("vsync")), self.last_row, 4, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.vsync_widget, self.last_row, 5)

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
        self.layout.addWidget(QtWidgets.QLabel(t("Video Speed")), self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.video_speed_widget, self.last_row, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Warning: Audio will not be modified")), self.last_row, 2, 1, 3)

    def init_tone_map(self):
        self.last_row += 1
        self.tone_map_widget = QtWidgets.QComboBox()
        self.tone_map_widget.addItems(["None", "clip", "linear", "gamma", "reinhard", "hable", "mobius"])
        self.tone_map_widget.setCurrentIndex(5)
        self.tone_map_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(
            QtWidgets.QLabel(t("HDR -> SDR Tone Map")), self.last_row, 0, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.tone_map_widget, self.last_row, 1)

    def init_denoise(self):
        self.last_row += 1
        self.denoise_type_widget = QtWidgets.QComboBox()
        self.denoise_type_widget.addItems(["None", "nlmeans", "atadenoise", "hqdn3d", "vaguedenoiser"])
        self.denoise_type_widget.setCurrentIndex(0)
        self.denoise_type_widget.currentIndexChanged.connect(self.page_update)

        self.denoise_strength_widget = QtWidgets.QComboBox()
        self.denoise_strength_widget.addItems(["weak", "moderate", "strong"])
        self.denoise_strength_widget.setCurrentIndex(0)
        self.denoise_strength_widget.currentIndexChanged.connect(self.page_update)

        self.layout.addWidget(QtWidgets.QLabel(t("Denoise")), self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_type_widget, self.last_row, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Strength")), self.last_row, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_strength_widget, self.last_row, 3)

    def init_deblock(self):
        self.last_row += 1
        self.deblock_widget = QtWidgets.QComboBox()
        self.deblock_widget.addItems(["None", "weak", "strong"])
        self.deblock_widget.setCurrentIndex(0)
        self.deblock_widget.currentIndexChanged.connect(self.page_update)

        self.deblock_size_widget = QtWidgets.QComboBox()
        self.deblock_size_widget.addItem("4")
        self.deblock_size_widget.addItems([str(x * 4) for x in range(2, 33, 2)])
        self.deblock_size_widget.addItems(["256", "512"])
        self.deblock_size_widget.currentIndexChanged.connect(self.page_update)
        self.deblock_size_widget.setCurrentIndex(2)

        self.layout.addWidget(QtWidgets.QLabel(t("Deblock")), self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_widget, self.last_row, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Block Size")), self.last_row, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_size_widget, self.last_row, 3)

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

        self.layout.addWidget(QtWidgets.QLabel(t("Color Primaries")), self.last_row, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_primaries_widget, self.last_row, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Transfer")), self.last_row, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_transfer_widget, self.last_row, 3)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Space")), self.last_row, 4, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_space_widget, self.last_row, 5)

    def init_vbv(self):
        self.last_row += 1
        self.maxrate_widget = QtWidgets.QLineEdit()
        self.maxrate_widget.setPlaceholderText("3000")
        self.maxrate_widget.setDisabled(True)
        self.maxrate_widget.setValidator(self.only_int)
        self.maxrate_widget.textChanged.connect(self.page_update)

        self.bufsize_widget = QtWidgets.QLineEdit()
        self.bufsize_widget.setPlaceholderText("3000")
        self.bufsize_widget.setDisabled(True)
        self.bufsize_widget.setValidator(self.only_int)
        self.bufsize_widget.textChanged.connect(self.page_update)

        self.vbv_checkbox = QtWidgets.QCheckBox(t("Enable VBV"))
        self.vbv_checkbox.toggled.connect(self.vbv_check_changed)

        self.layout.addWidget(
            QtWidgets.QLabel(f'{t("Maxrate")} (kbps)'), self.last_row, 0, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.maxrate_widget, self.last_row, 1)
        self.layout.addWidget(
            QtWidgets.QLabel(f'{t("Bufsize")} (kbps)'), self.last_row, 2, alignment=QtCore.Qt.AlignRight
        )
        self.layout.addWidget(self.bufsize_widget, self.last_row, 3)
        self.layout.addWidget(self.vbv_checkbox, self.last_row, 4)

    def vbv_check_changed(self):
        self.bufsize_widget.setEnabled(self.vbv_checkbox.isChecked())
        self.maxrate_widget.setEnabled(self.vbv_checkbox.isChecked())
        self.page_update()

    # def init_subtitle_overlay_fix(self):
    #     self.last_row += 1
    # TODO figure out overlay for subtitles move up
    # overlay=y=-140
    # crop=1904:800:6:140
    # (800 + 140) - 1080 == -140

    def update_settings(self):
        if self.updating or not self.app.fastflix.current_video:
            return False
        self.updating = True
        self.app.fastflix.current_video.video_settings.video_speed = video_speeds[self.video_speed_widget.currentText()]
        self.app.fastflix.current_video.video_settings.deblock = non(self.deblock_widget.currentText())
        self.app.fastflix.current_video.video_settings.deblock_size = int(self.deblock_size_widget.currentText())
        self.app.fastflix.current_video.video_settings.tone_map = self.tone_map_widget.currentText()
        self.app.fastflix.current_video.video_settings.vsync = non(self.vsync_widget.currentText())

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

        if self.vbv_checkbox.isChecked() and self.maxrate_widget.text() and self.bufsize_widget.text():
            self.app.fastflix.current_video.video_settings.maxrate = int(self.maxrate_widget.text())
            self.app.fastflix.current_video.video_settings.bufsize = int(self.bufsize_widget.text())
        else:
            self.app.fastflix.current_video.video_settings.maxrate = None
            self.app.fastflix.current_video.video_settings.bufsize = None

        self.updating = False

    def hdr_settings(self):
        if self.main.remove_hdr:
            self.color_primaries_widget.setCurrentText("bt709")
            self.app.fastflix.current_video.video_settings.color_primaries = "bt709"
            self.app.fastflix.current_video.video_settings.color_transfer = None
            self.app.fastflix.current_video.video_settings.color_space = None
            self.color_transfer_widget.setCurrentIndex(0)
            self.color_space_widget.setCurrentIndex(0)
        else:
            if self.app.fastflix.current_video:
                if self.app.fastflix.current_video.color_space:
                    self.color_space_widget.setCurrentText(self.app.fastflix.current_video.color_space)
                else:
                    self.color_space_widget.setCurrentIndex(0)

                if self.app.fastflix.current_video.color_transfer:
                    self.color_transfer_widget.setCurrentText(self.app.fastflix.current_video.color_transfer)
                else:
                    self.color_transfer_widget.setCurrentIndex(0)

                if self.app.fastflix.current_video.color_primaries:
                    self.color_primaries_widget.setCurrentText(self.app.fastflix.current_video.color_primaries)
                else:
                    self.color_primaries_widget.setCurrentIndex(0)
            else:
                self.color_space_widget.setCurrentIndex(0)
                self.color_transfer_widget.setCurrentIndex(0)
                self.color_primaries_widget.setCurrentIndex(0)

    def page_update(self):
        self.main.page_update(build_thumbnail=False)

    def reset(self, settings: VideoSettings = None):
        if settings:
            self.video_speed_widget.setCurrentText(get_key(video_speeds, settings.video_speed))
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
                self.vbv_checkbox.setChecked(True)
                self.maxrate_widget.setText(str(settings.maxrate))
                self.bufsize_widget.setText(str(settings.bufsize))
                self.maxrate_widget.setEnabled(True)
                self.bufsize_widget.setEnabled(True)
            else:
                self.vbv_checkbox.setChecked(False)
                self.maxrate_widget.setText("")
                self.bufsize_widget.setText("")
                self.maxrate_widget.setDisabled(True)
                self.bufsize_widget.setDisabled(True)

        else:
            self.video_speed_widget.setCurrentIndex(0)
            self.deblock_widget.setCurrentIndex(0)
            self.deblock_size_widget.setCurrentIndex(0)
            self.tone_map_widget.setCurrentIndex(5)
            self.incoming_same_as_source.setChecked(True)
            self.outgoing_same_as_source.setChecked(True)
            self.incoming_fps_widget.setDisabled(True)
            self.outgoing_fps_widget.setDisabled(True)
            self.incoming_fps_widget.setText("")
            self.outgoing_fps_widget.setText("")
            self.denoise_type_widget.setCurrentIndex(0)
            self.denoise_strength_widget.setCurrentIndex(0)
            self.vsync_widget.setCurrentIndex(0)
            self.vbv_checkbox.setChecked(False)
            self.maxrate_widget.setText("")
            self.bufsize_widget.setText("")
            self.maxrate_widget.setDisabled(True)
            self.bufsize_widget.setDisabled(True)

        self.hdr_settings()

        # Set the frame rate
        if self.app.fastflix.current_video:
            dont_set = False
            if "/" in self.app.fastflix.current_video.frame_rate:
                try:
                    over, under = self.app.fastflix.current_video.frame_rate.split("/")
                    if under == "1":
                        self.source_frame_rate.setText(over)
                        dont_set = True
                    readable_rate = int(over) / int(under)
                except Exception:
                    self.source_frame_rate.setText(self.app.fastflix.current_video.frame_rate)
                else:
                    if not dont_set:
                        self.source_frame_rate.setText(
                            f"{self.app.fastflix.current_video.frame_rate}   [ ~{readable_rate:.3f} ]"
                        )
            else:
                self.source_frame_rate.setText(self.app.fastflix.current_video.frame_rate)
            self.source_frame_rate_type.setText(
                t("Constant")
                if self.app.fastflix.current_video.frame_rate == self.app.fastflix.current_video.average_frame_rate
                else t("Variable")
            )
        else:
            self.source_frame_rate.setText("")
            self.source_frame_rate_type.setText("")

    def new_source(self):
        self.reset()

        if self.app.fastflix.current_video.color_primaries in ffmpeg_valid_color_primaries:
            self.color_primaries_widget.setCurrentIndex(
                ffmpeg_valid_color_primaries.index(self.app.fastflix.current_video.color_primaries) + 1
            )
        else:
            self.color_primaries_widget.setCurrentIndex(0)

        if self.app.fastflix.current_video.color_transfer in ffmpeg_valid_color_transfers:
            self.color_transfer_widget.setCurrentIndex(
                ffmpeg_valid_color_transfers.index(self.app.fastflix.current_video.color_transfer) + 1
            )
        else:
            self.color_transfer_widget.setCurrentIndex(0)

        if self.app.fastflix.current_video.color_space in ffmpeg_valid_color_space:
            self.color_space_widget.setCurrentIndex(
                ffmpeg_valid_color_space.index(self.app.fastflix.current_video.color_space) + 1
            )
        else:
            self.color_space_widget.setCurrentIndex(0)
