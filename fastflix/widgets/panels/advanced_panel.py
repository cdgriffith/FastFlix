#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from typing import List, Union

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import AttachmentTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import link

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
    if value == "none":
        return None
    return value


# TODO disable fps boxes if same as source
# TODO reset from queue


class AdvancedPanel(QtWidgets.QWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()

        self.layout = QtWidgets.QGridLayout()

        self.init_fps()
        self.init_video_speed()
        self.init_tone_map()
        self.init_denoise()
        self.init_deblock()
        self.init_color_info()
        self.init_vsync()
        self.layout.setRowStretch(8, True)
        self.setLayout(self.layout)

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

        self.layout.addWidget(QtWidgets.QLabel(t("Override Source FPS")), 0, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.incoming_fps_widget, 0, 1)
        self.layout.addWidget(self.incoming_same_as_source, 0, 2)
        self.layout.addWidget(QtWidgets.QLabel(t("Source Frame Rate:")), 0, 3, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.source_frame_rate, 0, 4)

        self.layout.addWidget(QtWidgets.QLabel(t("Output FPS")), 1, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.outgoing_fps_widget, 1, 1)
        self.layout.addWidget(self.outgoing_same_as_source, 1, 2)

    def fps_update(self, myself, widget):
        widget.setDisabled(myself.isChecked())
        self.page_update()

    def init_concat(self):
        layout = QtWidgets.QHBoxLayout()
        self.concat_widget = QtWidgets.QCheckBox(t("Combine Files"))
        # TODO add "learn more" link

        layout.addWidget(self.concat_widget)
        return layout

    def init_video_speed(self):
        self.video_Speed_widget = QtWidgets.QComboBox()
        self.video_Speed_widget.addItems(video_speeds.keys())
        self.video_Speed_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(QtWidgets.QLabel(t("Video Speed")), 2, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.video_Speed_widget, 2, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Warning: Audio will not be modified")), 2, 2)

    def init_tone_map(self):
        self.tone_map_widget = QtWidgets.QComboBox()
        self.tone_map_widget.addItems(["None", "clip", "linear", "gamma", "reinhard", "hable", "mobius"])
        self.tone_map_widget.setCurrentIndex(5)
        self.tone_map_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(QtWidgets.QLabel(t("HDR -> SDR Tone Map")), 3, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.tone_map_widget, 3, 1)

    def init_denoise(self):
        self.denoise_type_widget = QtWidgets.QComboBox()
        self.denoise_type_widget.addItems(["None", "nlmeans", "atadenoise", "hqdn3d", "vaguedenoiser"])
        self.denoise_type_widget.setCurrentIndex(0)
        self.denoise_type_widget.currentIndexChanged.connect(self.page_update)

        self.denoise_strength_widget = QtWidgets.QComboBox()
        self.denoise_strength_widget.addItems(["weak", "moderate", "strong"])
        self.denoise_strength_widget.setCurrentIndex(0)
        self.denoise_strength_widget.currentIndexChanged.connect(self.page_update)

        self.layout.addWidget(QtWidgets.QLabel(t("Denoise")), 4, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_type_widget, 4, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Strength")), 4, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.denoise_strength_widget, 4, 3)

    def init_deblock(self):
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

        self.layout.addWidget(QtWidgets.QLabel(t("Deblock")), 5, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_widget, 5, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Block Size")), 5, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.deblock_size_widget, 5, 3)

    def init_color_info(self):
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

        self.layout.addWidget(QtWidgets.QLabel(t("Color Primaries")), 6, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_primaries_widget, 6, 1)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Transfer")), 6, 2, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_transfer_widget, 6, 3)
        self.layout.addWidget(QtWidgets.QLabel(t("Color Space")), 6, 4, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.color_space_widget, 6, 5)

    def init_vsync(self):
        self.vsync_widget = QtWidgets.QComboBox()
        self.vsync_widget.addItem(t("Unspecified"))
        self.vsync_widget.addItems(vsync)
        self.vsync_widget.currentIndexChanged.connect(self.page_update)
        self.layout.addWidget(QtWidgets.QLabel(t("vsync")), 7, 0, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.vsync_widget, 7, 1)

    def update_settings(self):
        self.app.fastflix.current_video.video_settings.speed = video_speeds[self.video_Speed_widget.currentText()]
        self.app.fastflix.current_video.video_settings.deblock = non(self.deblock_widget.currentText())
        self.app.fastflix.current_video.video_settings.deblock_size = int(self.deblock_size_widget.currentText())
        self.app.fastflix.current_video.video_settings.tone_map = non(self.tone_map_widget.currentText())
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

    def page_update(self):
        self.main.page_update(build_thumbnail=False)

    def reset(self, reload=False):
        if reload:
            vs = self.app.fastflix.current_video.video_settings
            # TODO reload from queue
        else:
            self.video_Speed_widget.setCurrentIndex(0)
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
                            f"{self.app.fastflix.current_video.frame_rate} (~{readable_rate:.3f})"
                        )
            else:
                self.source_frame_rate.setText(self.app.fastflix.current_video.frame_rate)

        # "r_frame_rate"

        #
        #     if not self.incoming_same_as_source.isChecked():
        #         self.app.fastflix.current_video.video_settings.source_fps = self.incoming_fps_widget.text()
        #     if not self.outgoing_same_as_source.isChecked():
        #         self.app.fastflix.current_video.video_settings.output_fps = self.outgoing_fps_widget.text()

    def new_source(self):
        self.reset(reload=False)

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
