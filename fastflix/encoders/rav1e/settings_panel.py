#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel

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
    '50 - "I\'m just testing to see if this works"',
    "Custom",
]
pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]


class RAV1E(SettingPanel):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        grid = QtWidgets.QGridLayout()

        self.mode = "QP"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self._add_remove_hdr(), 1, 0, 1, 2)
        grid.addLayout(self.init_tiles(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 4, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 5, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 6, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 4, 4)
        grid.addLayout(self.init_single_pass(), 4, 2, 1, 1)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.setRowStretch(9, 1)
        guide_label = QtWidgets.QLabel(
            f"<a href='https://github.com/xiph/rav1e/blob/master/README.md'>rav1e github</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    def init_speed(self):
        return self._add_combo_box(
            label="Speed",
            tooltip="Quality/Speed ratio modifier (defaults to -1)",
            options=[str(x) for x in range(-1, 11)],
            widget_name="speed",
        )

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Break the video into rows to encode faster (lesser quality)",
            options=[str(x) for x in range(-1, 17)],
            widget_name="tile_rows",
            default=1,
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Break the video into columns to encode faster (lesser quality)",
            options=[str(x) for x in range(-1, 17)],
            widget_name="tile_columns",
            default=1,
        )

    def init_tiles(self):
        return self._add_combo_box("Tiles", [str(x) for x in range(-1, 17)], "tiles", default=1)

    def init_single_pass(self):
        return self._add_check_box("Single Pass (Bitrate)", "single_pass", checked=True)

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            default=1,
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            default=1,
        )

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        qp_group_box = QtWidgets.QGroupBox()
        qp_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        qp_box_layout = QtWidgets.QHBoxLayout()

        # rotation_dir = Path(base_path, 'data', 'rotations')
        # group_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-15px; padding-bottom:-5px}")
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        bitrate_radio = QtWidgets.QRadioButton("Bitrate")
        bitrate_radio.setFixedWidth(80)
        self.widgets.mode.addButton(bitrate_radio)
        self.widgets.bitrate = QtWidgets.QComboBox()
        self.widgets.bitrate.setFixedWidth(250)
        self.widgets.bitrate.addItems(recommended_bitrates)
        self.widgets.bitrate.setCurrentIndex(6)
        self.widgets.bitrate.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_bitrate = QtWidgets.QLineEdit("3000")
        self.widgets.custom_bitrate.setFixedWidth(100)
        self.widgets.custom_bitrate.setDisabled(True)
        self.widgets.custom_bitrate.textChanged.connect(lambda: self.main.build_commands())
        bitrate_box_layout.addWidget(bitrate_radio)
        bitrate_box_layout.addWidget(self.widgets.bitrate)
        bitrate_box_layout.addStretch()
        bitrate_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        bitrate_box_layout.addWidget(self.widgets.custom_bitrate)

        qp_radio = QtWidgets.QRadioButton("QP")
        qp_radio.setChecked(True)
        qp_radio.setFixedWidth(80)
        self.widgets.mode.addButton(qp_radio)

        self.widgets.qp = QtWidgets.QComboBox()
        self.widgets.qp.setFixedWidth(250)
        self.widgets.qp.addItems(recommended_qp)
        self.widgets.qp.setCurrentIndex(0)
        self.widgets.qp.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_qp = QtWidgets.QLineEdit("30")
        self.widgets.custom_qp.setFixedWidth(100)
        self.widgets.custom_qp.setDisabled(True)
        self.widgets.custom_qp.setValidator(self.only_int)
        self.widgets.custom_qp.textChanged.connect(lambda: self.main.build_commands())
        qp_box_layout.addWidget(qp_radio)
        qp_box_layout.addWidget(self.widgets.qp)
        qp_box_layout.addStretch()
        qp_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        qp_box_layout.addWidget(self.widgets.custom_qp)

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        layout.addWidget(qp_group_box, 0, 0)
        layout.addWidget(bitrate_group_box, 1, 0)
        return layout

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def get_settings(self):
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            speed=self.widgets.speed.currentText(),
            tile_columns=int(self.widgets.tile_columns.currentText()),
            tile_rows=int(self.widgets.tile_rows.currentText()),
            tiles=int(self.widgets.tiles.currentText()),
            single_pass=self.widgets.single_pass.isChecked(),
            max_mux=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
        )
        if self.mode == "QP":
            qp = self.widgets.qp.currentText()
            settings.qp = int(qp.split(" ", 1)[0]) if qp.lower() != "custom" else self.widgets.custom_qp.text()
        else:
            bitrate = self.widgets.bitrate.currentText()
            settings.bitrate = (
                bitrate.split(" ", 1)[0] if bitrate.lower() != "custom" else self.widgets.custom_bitrate.text()
            )
        return settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
