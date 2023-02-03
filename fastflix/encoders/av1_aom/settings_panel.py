# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import AOMAV1Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "100k   (320x240p @ 24,25,30)",
    "200k   (640x360p @ 24,25,30)",
    "400k   (640x480p @ 24,25,30)",
    "800k  (1280x720p @ 24,25,30)",
    "1200k (1280x720p @ 50,60)",
    "1200k (1920x1080p @ 24,25,30)",
    "2000k (1920x1080p @ 50,60)",
    "4000k (2560x1440p @ 24,25,30)",
    "6000k (2560x1440p @ 50,60)",
    "9000k (3840x2160p @ 24,25,30)",
    "13000k (3840x2160p @ 50,60)",
    "Custom",
]

recommended_crfs = ["34", "32", "30", "28", "26", "24", "22", "20", "Custom"]

pix_fmts = [
    "8-bit: yuv420p",
    "10-bit: yuv420p10le",
    "12-bit: yuv420p12le",
    "8-bit 422: yuv422p",
    "8-bit 444: yuv444p",
    "10-bit 422: yuv422p10le",
    "10-bit 444: yuv444p10le",
    "12-bit 422: yuv422p12le",
    "12-bit 444: yuv444p12le",
]


class AV1(SettingPanel):
    profile_name = "aom_av1"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("FFMPEG libaom-av1_aom"), 0, 0)

        self.widgets = Box(fps=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self.init_cpu_used(), 0, 0, 1, 2)
        grid.addLayout(self.init_row_mt(), 1, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_usage(), 4, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 5, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 6, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        grid.addLayout(self._add_custom(), 10, 0, 1, 6)
        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            link("https://trac.ffmpeg.org/wiki/Encode/AV1", t("FFMPEG AV1 Encoding Guide"), app.fastflix.config.theme)
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)

        self.setLayout(grid)
        self.hide()

    def init_cpu_used(self):
        return self._add_combo_box(
            label="CPU Used",
            tooltip="Quality/Speed ratio modifier (defaults to 4)",
            widget_name="cpu_used",
            options=[str(x) for x in range(0, 9)],
            opt="cpu_used",
        )

    def init_row_mt(self):
        return self._add_combo_box(
            label="Row Multi-Threading",
            tooltip="Enable row based multi-threading",
            widget_name="row_mt",
            options=["default", "enabled", "disabled"],
            opt="row_mt",
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Log2 of number of tile columns to encode faster (lesser quality)",
            widget_name="tile_columns",
            options=[str(x) for x in range(-1, 7)],
            opt="tile_columns",
        )

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Log2 of number of tile rows to encode faster (lesser quality)",
            widget_name="tile_rows",
            options=[str(x) for x in range(-1, 7)],
            opt="tile_rows",
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

    def init_usage(self):
        return self._add_combo_box(
            label="Usage",
            tooltip="Quality and compression efficiency vs speed trade-off",
            widget_name="usage",
            options=["good", "realtime"],
            opt="usage",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_crfs, qp_name="crf")

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        settings = AOMAV1Settings(
            usage=self.widgets.usage.currentText(),
            cpu_used=self.widgets.cpu_used.currentText(),
            row_mt=self.widgets.row_mt.currentText(),
            tile_rows=self.widgets.tile_rows.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.crf = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
