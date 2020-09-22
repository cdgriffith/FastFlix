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


class SVT_AV1(SettingPanel):
    def __init__(self, parent, main):
        super(SVT_AV1, self).__init__(parent)
        self.main = main
        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, remove_hdr=None, mode=None, segment_size=None)

        self.mode = "QP"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self._add_remove_hdr(), 1, 0, 1, 2)
        grid.addLayout(self.init_pix_fmts(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 4, 0, 1, 2)
        grid.addLayout(self.init_tier(), 5, 0, 1, 2)
        grid.addLayout(self.init_sc_detection(), 6, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 7, 0, 1, 2)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.addLayout(self.init_modes(), 0, 2, 4, 4)
        grid.addLayout(self.init_single_pass(), 4, 2, 1, 1)
        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            f"<a href='https://github.com/AOMediaCodec/SVT-AV1/blob/master/Docs/svt-av1_encoder_user_guide.md'>SVT-AV1 Encoding Guide</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    def init_tile_rows(self):
        return self._add_combo_box(label="Tile Rows", options=[str(x) for x in range(0, 7)], widget_name="tile_rows")

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns", options=[str(x) for x in range(0, 5)], widget_name="tile_columns"
        )

    def init_pix_fmts(self):
        return self._add_combo_box(label="Bit Depth", options=pix_fmts, widget_name="pix_fmt", default=1)

    def init_tier(self):
        return self._add_combo_box(label="Tier", options=["main", "high"], widget_name="tier")

    def init_sc_detection(self):
        return self._add_combo_box(label="Scene Detection", options=["false", "true"], widget_name="sc_detection")

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            default=1,
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
        return self._add_combo_box(label="Speed", widget_name="speed", options=[str(x) for x in range(9)], default=7)

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
            single_pass=self.widgets.single_pass.isChecked(),
            tier=int(self.widgets.tier.currentIndex()),
            sc_detection=int(self.widgets.sc_detection.currentIndex()),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            max_mux=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
        )
        if self.mode == "QP":
            qp = self.widgets.qp.currentText()
            settings.qp = int(qp.split(" ", 1)[0]) if qp.lower() != "custom" else self.widgets.custom_qp.text()
        else:
            bitrate = self.widgets.bitrate.currentText()
            settings.bitrate = bitrate.split(" ", 1)[0] if bitrate.lower() != "custom" else self.widgets.bitrate.text()
        return settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
