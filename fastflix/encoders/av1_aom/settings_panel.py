# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel

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

pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]


class AV1(SettingPanel):
    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.main = main

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("FFMPEG libaom-av1_aom"), 0, 0)

        self.widgets = Box(fps=None, remove_hdr=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self._add_remove_hdr(), 0, 0, 1, 2)
        grid.addLayout(self.init_cpu_used(), 1, 0, 1, 2)
        grid.addLayout(self.init_row_mt(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 4, 0, 1, 2)
        grid.addLayout(self.init_usage(), 5, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 6, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 7, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        grid.addLayout(self._add_custom(), 10, 0, 1, 6)
        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            f"<a href='https://trac.ffmpeg.org/wiki/Encode/AV1'>FFMPEG AV1 Encoding Guide</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)

        self.setLayout(grid)
        self.hide()

    def init_cpu_used(self):
        return self._add_combo_box(
            label="CPU Used",
            tooltip="Quality/Speed ratio modifier (defaults to 1)",
            widget_name="cpu_used",
            options=[str(x) for x in range(0, 9)],
            default=1,
        )

    def init_row_mt(self):
        return self._add_combo_box(
            label="Row Multi-Threading",
            tooltip="Enable row based multi-threading",
            widget_name="row_mt",
            options=["default", "enabled", "disabled"],
            default=0,
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Log2 of number of tile columns to encode faster (lesser quality)",
            widget_name="tile_columns",
            options=[str(x) for x in range(-1, 7)],
            default=0,
        )

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Log2 of number of tile rows to encode faster (lesser quality)",
            widget_name="tile_rows",
            options=[str(x) for x in range(-1, 7)],
            default=0,
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            default=1,
        )

    def init_usage(self):
        return self._add_combo_box(
            label="Usage",
            tooltip="Quality and compression efficiency vs speed trade-off",
            widget_name="usage",
            options=["good", "realtime"],
            default=0,
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            default=1,
        )

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        crf_group_box = QtWidgets.QGroupBox()
        crf_group_box.setFixedHeight(40)
        crf_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        crf_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setFixedHeight(40)
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        bitrate_radio = QtWidgets.QRadioButton("Bitrate")
        self.widgets.mode.addButton(bitrate_radio)
        self.widgets.bitrate = QtWidgets.QComboBox()
        self.widgets.bitrate.addItems(recommended_bitrates)
        self.widgets.bitrate.setCurrentIndex(6)
        self.widgets.bitrate.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_bitrate = QtWidgets.QLineEdit("3000")
        self.widgets.custom_bitrate.setFixedWidth(100)
        self.widgets.custom_bitrate.setDisabled(True)
        self.widgets.custom_bitrate.textChanged.connect(lambda: self.main.build_commands())
        bitrate_box_layout.addWidget(bitrate_radio)
        bitrate_box_layout.addWidget(self.widgets.bitrate)
        bitrate_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        bitrate_box_layout.addWidget(self.widgets.custom_bitrate)

        crf_radio = QtWidgets.QRadioButton("CRF")
        crf_radio.setChecked(True)
        self.widgets.mode.addButton(crf_radio)

        self.widgets.crf = QtWidgets.QComboBox()
        self.widgets.crf.addItems(recommended_crfs)
        self.widgets.crf.setCurrentIndex(2)
        self.widgets.crf.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_crf = QtWidgets.QLineEdit("30")
        self.widgets.custom_crf.setFixedWidth(100)
        self.widgets.custom_crf.setDisabled(True)
        self.widgets.custom_crf.setValidator(self.only_int)
        self.widgets.custom_crf.textChanged.connect(lambda: self.main.build_commands())
        crf_box_layout.addWidget(crf_radio)
        crf_box_layout.addWidget(self.widgets.crf)
        crf_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        crf_box_layout.addWidget(self.widgets.custom_crf)

        bitrate_group_box.setLayout(bitrate_box_layout)
        crf_group_box.setLayout(crf_box_layout)

        layout.addWidget(crf_group_box, 0, 0)
        layout.addWidget(bitrate_group_box, 1, 0)
        return layout

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def get_settings(self):
        conversions = {"default": None, "enabled": 1, "disabled": 0}

        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            usage=self.widgets.usage.currentText(),
            cpu_used=self.widgets.cpu_used.currentText(),
            row_mt=conversions[self.widgets.row_mt.currentText()],
            tile_rows=self.widgets.tile_rows.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            max_mux=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
        )

        if self.mode == "CRF":
            crf = self.widgets.crf.currentText()
            settings.crf = int(crf.split(" ", 1)[0]) if crf.lower() != "custom" else self.widgets.custom_crf.text()
        else:
            bitrate = self.widgets.bitrate.currentText()
            settings.bitrate = (
                bitrate.split(" ", 1)[0] if bitrate.lower() != "custom" else self.widgets.custom_bitrate.text()
            )
        return settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
