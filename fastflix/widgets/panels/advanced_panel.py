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
    "1/5": 5,
    "1/4": 4,
    "1/3": 3,
    "1/2": 2,
    "2/3": 1.67,
    "3/4": 1.5,
    "1.5x": 0.75,
    "2x": 0.5,
    "3x": 0.34,
    "4x": 0.25,
    "5x": 0.2,
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


def non(value):
    if value == "none":
        return None
    return value


# TODO align the things
# TODO disable fps boxes if same as source
# TODO reset from queue

class AdvancedPanel(QtWidgets.QWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()

        layout = QtWidgets.QGridLayout()

        layout.addLayout(self.init_fps(), 0, 0, 1, 6)
        # layout.addLayout(self.init_concat(), 1, 0, 1, 6)
        layout.addLayout(self.init_video_speed(), 2, 0, 1, 6)
        layout.addLayout(self.init_tone_map(), 3, 0, 1, 6)
        layout.addLayout(self.init_denoise(), 4, 0, 1, 6)
        layout.addLayout(self.init_deblock(), 5, 0, 1, 6)
        layout.addLayout(QtWidgets.QHBoxLayout(), 6, 0, 5, 6, stretch=True)

        # row, column, row span, column span
        # layout.addWidget(QtWidgets.QLabel(t("Poster Cover")), 0, 0, 1, 5)
        # layout.addWidget(QtWidgets.QLabel(t("Landscape Cover")), 0, 6, 1, 4)
        # info_label = QtWidgets.QLabel(
        #     link("https://codecalamity.com/guides/video-thumbnails/", t("Enabling cover thumbnails on your system"))
        # )
        # info_label.setOpenExternalLinks(True)
        # layout.addWidget(info_label, 10, 0, 1, 9, QtCore.Qt.AlignLeft)
        #
        # poster_options_layout = QtWidgets.QHBoxLayout()
        # self.cover_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Cover"))
        # self.small_cover_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Small Cover (no preview)"))
        #
        # poster_options_layout.addWidget(self.cover_passthrough_checkbox)
        # poster_options_layout.addWidget(self.small_cover_passthrough_checkbox)
        #
        # land_options_layout = QtWidgets.QHBoxLayout()
        # self.cover_land_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Landscape Cover"))
        # self.small_cover_land_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Small Landscape Cover  (no preview)"))
        #
        # land_options_layout.addWidget(self.cover_land_passthrough_checkbox)
        # land_options_layout.addWidget(self.small_cover_land_passthrough_checkbox)
        #
        # self.cover_passthrough_checkbox.toggled.connect(lambda: self.cover_passthrough_check())
        # self.small_cover_passthrough_checkbox.toggled.connect(lambda: self.small_cover_passthrough_check())
        # self.cover_land_passthrough_checkbox.toggled.connect(lambda: self.cover_land_passthrough_check())
        # self.small_cover_land_passthrough_checkbox.toggled.connect(lambda: self.small_cover_land_passthrough_check())
        #
        # self.poster = QtWidgets.QLabel()
        # self.poster.setSizePolicy(sp)
        #
        # self.landscape = QtWidgets.QLabel()
        # self.landscape.setSizePolicy(sp)
        #
        # layout.addLayout(poster_options_layout, 1, 0, 1, 4)
        # layout.addLayout(land_options_layout, 1, 6, 1, 4)
        #
        # layout.addWidget(self.poster, 2, 0, 8, 4)
        # layout.addWidget(self.landscape, 2, 6, 8, 4)
        #
        # layout.addLayout(self.init_cover(), 9, 0, 1, 4)
        # layout.addLayout(self.init_landscape_cover(), 9, 6, 1, 4)
        # layout.rowStretch(10)

        self.setLayout(layout)

    def init_denoise(self):
        layout = QtWidgets.QHBoxLayout()

        self.denoise_type_widget = QtWidgets.QComboBox()
        self.denoise_type_widget.addItems(["none", "nlmeans", "atadenoise", "hqdn3d", "vaguedenoiser"])
        self.denoise_type_widget.setCurrentIndex(0)
        self.denoise_type_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(QtWidgets.QLabel(t("Denoise")))
        layout.addWidget(self.denoise_type_widget)

        self.denoise_strength_widget = QtWidgets.QComboBox()
        self.denoise_strength_widget.addItems(["weak", "moderate", "strong"])
        self.denoise_strength_widget.setCurrentIndex(0)
        self.denoise_strength_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(QtWidgets.QLabel(t("Strength")))
        layout.addWidget(self.denoise_strength_widget)
        layout.addStretch(True)
        return layout

    def init_fps(self):
        layout = QtWidgets.QHBoxLayout()
        self.incoming_fps_widget = QtWidgets.QLineEdit()
        self.incoming_fps_widget.setDisabled(False)
        self.incoming_fps_widget.textChanged.connect(lambda: self.main.page_update())
        self.outgoing_fps_widget = QtWidgets.QLineEdit()
        self.outgoing_fps_widget.setDisabled(False)
        self.outgoing_fps_widget.textChanged.connect(lambda: self.main.page_update())
        self.incoming_same_as_source = QtWidgets.QCheckBox(t("Same as Source"))
        self.incoming_same_as_source.setChecked(True)
        self.incoming_same_as_source.toggled.connect(lambda: self.main.page_update())
        self.outgoing_same_as_source = QtWidgets.QCheckBox(t("Same as Source"))
        self.outgoing_same_as_source.setChecked(True)
        self.outgoing_same_as_source.toggled.connect(lambda: self.main.page_update())

        self.source_frame_rate = QtWidgets.QLabel("")
        layout.addWidget(QtWidgets.QLabel(t("Source Frame Rate:")))
        layout.addWidget(self.source_frame_rate)
        layout.addStretch(True)
        layout.addWidget(QtWidgets.QLabel(t("Override Source FPS")))
        layout.addWidget(self.incoming_fps_widget)
        layout.addWidget(self.incoming_same_as_source)
        # layout.addWidget(self.incoming_fps_widget) spacer
        layout.addStretch(True)
        layout.addWidget(QtWidgets.QLabel(t("Output FPS")))
        layout.addWidget(self.outgoing_fps_widget)
        layout.addWidget(self.outgoing_same_as_source)

        # TODO add connects and page updates

        return layout

    def init_concat(self):
        layout = QtWidgets.QHBoxLayout()
        self.concat_widget = QtWidgets.QCheckBox(t("Combine Files"))
        # TODO add "learn more" link

        layout.addWidget(self.concat_widget)
        return layout

    def init_video_speed(self):
        layout = QtWidgets.QHBoxLayout()

        self.video_Speed_widget = QtWidgets.QComboBox()
        self.video_Speed_widget.addItem(t("Same as Source"))
        self.video_Speed_widget.addItems(video_speeds.keys())
        self.video_Speed_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(QtWidgets.QLabel(t("Video Speed")))
        layout.addWidget(self.video_Speed_widget)
        layout.addWidget(QtWidgets.QLabel(t("Warning: Audio will not be modified")))
        layout.addStretch()
        return layout

    def init_tone_map(self):
        layout = QtWidgets.QHBoxLayout()

        self.tone_map_widget = QtWidgets.QComboBox()
        self.tone_map_widget.addItems(["none", "clip", "linear", "gamma", "reinhard", "hable", "mobius"])
        self.tone_map_widget.setCurrentIndex(5)
        self.tone_map_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(QtWidgets.QLabel(t("HDR -> SDR Tone Map")))
        layout.addWidget(self.tone_map_widget)
        layout.addStretch(True)
        return layout

    def init_deblock(self):
        layout = QtWidgets.QHBoxLayout()

        self.deblock_widget = QtWidgets.QComboBox()
        self.deblock_widget.addItems(["none", "weak", "strong"])
        self.deblock_widget.setCurrentIndex(0)
        self.deblock_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(QtWidgets.QLabel(t("Deblock")))
        layout.addWidget(self.deblock_widget)

        self.deblock_size_widget = QtWidgets.QComboBox()
        self.deblock_size_widget.addItem("4")
        self.deblock_size_widget.addItems([str(x * 4) for x in range(2, 33, 2)])
        self.deblock_size_widget.addItems(["256", "512"])
        self.deblock_size_widget.currentIndexChanged.connect(lambda: self.main.page_update())
        self.deblock_size_widget.setCurrentIndex(2)

        layout.addWidget(QtWidgets.QLabel(t("Block Size")))
        layout.addWidget(self.deblock_size_widget)
        layout.addStretch(True)

        return layout

    def update_settings(self):
        self.app.fastflix.current_video.video_settings.speed = video_speeds[self.video_Speed_widget.currentText()]
        self.app.fastflix.current_video.video_settings.deblock = non(self.deblock_widget.currentText())
        self.app.fastflix.current_video.video_settings.deblock_size = int(self.deblock_size_widget.currentText())
        self.app.fastflix.current_video.video_settings.tone_map = non(self.tone_map_widget.currentText())
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

    def reset(self, reload=False):
        if not reload:
            self.video_Speed_widget.setCurrentIndex(0)
            self.deblock_widget.setCurrentIndex(0)
            self.deblock_size_widget.setCurrentIndex(0)
            self.tone_map_widget.setCurrentIndex(5)
            self.incoming_same_as_source.setChecked(True)
            self.outgoing_same_as_source.setChecked(True)
            self.incoming_fps_widget.setText("")
            self.outgoing_fps_widget.setText("")
            self.denoise_type_widget.setCurrentIndex(0)
            self.denoise_strength_widget.setCurrentIndex(0)
        else:
            vs = self.app.fastflix.current_video.video_settings

        if self.app.fastflix.current_video:
            if "/" in self.app.fastflix.current_video.frame_rate:
                try:
                    over, under = self.app.fastflix.current_video.frame_rate.split("/")
                    readable_rate = int(over) / int(under)
                except Exception:
                    self.source_frame_rate.setText(self.app.fastflix.current_video.frame_rate)
                else:
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

    # def init_cover(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     self.cover_path = QtWidgets.QLineEdit()
    #     self.cover_path.textChanged.connect(lambda: self.update_cover())
    #     self.cover_button = QtWidgets.QPushButton(
    #         icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
    #     )
    #     self.cover_button.clicked.connect(lambda: self.select_cover())
    #
    #     layout.addWidget(self.cover_path)
    #     layout.addWidget(self.cover_button)
    #     return layout

    # def update_filter_settings(self):
    #     self.app.fastflix.current_video.video_settings.attachment_tracks = attachments

    def new_source(self):
        pass
