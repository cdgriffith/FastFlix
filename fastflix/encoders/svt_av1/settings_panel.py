#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k   (320x240p @ 30fps)",
    "276k   (640x360p @ 30fps)",
    "512k   (640x480p @ 30fps)",
    "1024k  (1280x720p @ 30fps)",
    "1800k (1280x720p @ 60fps)",
    "1800k (1920x1080p @ 30fps)",
    "3000k (1920x1080p @ 60fps)",
    "6000k (2560x1440p @ 30fps)",
    "9000k (2560x1440p @ 60fps)",
    "12000k (3840x2160p @ 30fps)",
    "18000k (3840x2160p @ 60fps)",
    "Custom",
]

recommended_qp = [
    "20",
    "21",
    "22",
    "23",
    "24 - recommended",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30 - standard",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    '50 - "I\'m just testing to see if this works"',
    "Custom",
]
pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]


class SVT_AV1(SettingPanel):
    profile_name = "svt_av1"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None, segment_size=None)

        self.mode = "QP"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 1, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 3, 0, 1, 2)
        grid.addLayout(self.init_tier(), 4, 0, 1, 2)
        # grid.addLayout(self.init_sc_detection(), 6, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 5, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self.init_single_pass(), 5, 2, 1, 1)

        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            link(
                "https://github.com/AOMediaCodec/SVT-AV1/blob/master/Docs/svt-av1_encoder_user_guide.md",
                t("SVT-AV1 Encoding Guide"),
                app.fastflix.config.theme,
            )
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)
        grid.addWidget(guide_label, 11, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Break the video into rows to encode faster (lesser quality)",
            options=[str(x) for x in range(0, 7)],
            widget_name="tile_rows",
            opt="tile_rows",
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Break the video into columns to encode faster (lesser quality)",
            options=[str(x) for x in range(0, 5)],
            widget_name="tile_columns",
            opt="tile_columns",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_tier(self):
        return self._add_combo_box(label="Tier", options=["main", "high"], widget_name="tier", opt="tier")

    def init_sc_detection(self):
        return self._add_combo_box(
            label="Scene Detection", options=["false", "true"], widget_name="sc_detection", opt="scene_detection"
        )

    def init_single_pass(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Single Pass"))
        self.widgets.single_pass = QtWidgets.QCheckBox()
        self.widgets.single_pass.setChecked(False)
        self.widgets.single_pass.toggled.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.single_pass)
        return layout

    def init_speed(self):
        return self._add_combo_box(
            label="Speed",
            widget_name="speed",
            options=[str(x) for x in range(9)],
            tooltip="Quality/Speed ratio modifier",
            opt="speed",
        )

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_qp, qp_name="qp")

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        settings = SVTAV1Settings(
            speed=self.widgets.speed.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            tile_rows=self.widgets.tile_rows.currentText(),
            single_pass=self.widgets.single_pass.isChecked(),
            tier=self.widgets.tier.currentText(),
            # scene_detection=int(self.widgets.sc_detection.currentIndex()),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
