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


class AV1(SettingPanel):
    def __init__(self, parent, main):
        super(AV1, self).__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("FFMPEG libaom-av1_aom"), 0, 0)

        self.widgets = Box(fps=None, remove_hdr=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self.init_remove_hdr(), 0, 0, 1, 2)
        grid.addLayout(self.init_cpu_used(), 1, 0, 1, 2)
        grid.addLayout(self.init_row_mt(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 4, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 3, 3)

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
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("CPU Used")
        label.setToolTip("Quality/Speed ratio modifier (defaults to 1)")
        layout.addWidget(label)
        self.widgets.cpu_used = QtWidgets.QComboBox()
        self.widgets.cpu_used.addItems([str(x) for x in range(0, 9)])
        self.widgets.cpu_used.setCurrentIndex(1)
        self.widgets.cpu_used.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.cpu_used)
        return layout

    def init_row_mt(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Row Multi-Threading")
        label.setToolTip("Enable row based multi-threading")
        layout.addWidget(label)
        self.widgets.row_mt = QtWidgets.QComboBox()
        self.widgets.row_mt.addItems(["default", "enabled", "disabled"])
        self.widgets.row_mt.setCurrentIndex(0)
        self.widgets.row_mt.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.row_mt)
        return layout

    def init_tile_columns(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Tile Columns")
        label.setToolTip("Log2 of number of tile columns to use")
        layout.addWidget(label)
        self.widgets.tile_columns = QtWidgets.QComboBox()
        self.widgets.tile_columns.addItems([str(x) for x in range(-1, 7)])
        self.widgets.tile_columns.setCurrentIndex(0)
        self.widgets.tile_columns.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.tile_columns)
        return layout

    def init_tile_rows(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Tile Rows")
        label.setToolTip("Log2 of number of tile rows to use")
        layout.addWidget(label)
        self.widgets.tile_rows = QtWidgets.QComboBox()
        self.widgets.tile_rows.addItems([str(x) for x in range(-1, 7)])
        self.widgets.tile_rows.setCurrentIndex(0)
        self.widgets.tile_rows.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.tile_rows)
        return layout

    def init_remove_hdr(self):
        layout = QtWidgets.QHBoxLayout()
        self.remove_hdr_label = QtWidgets.QLabel("Remove HDR")
        self.remove_hdr_label.setToolTip(
            "Convert BT2020 colorspace into bt709\n " "WARNING: This will take much longer and result in a larger file"
        )
        layout.addWidget(self.remove_hdr_label)
        self.widgets.remove_hdr = QtWidgets.QComboBox()
        self.widgets.remove_hdr.addItems(["No", "Yes"])
        self.widgets.remove_hdr.setCurrentIndex(0)
        self.widgets.remove_hdr.setDisabled(True)
        self.widgets.remove_hdr.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.remove_hdr)
        return layout

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
        # rotation_dir = Path(base_path, 'data', 'rotations')
        # group_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-15px; padding-bottom:-5px}")
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
        print(self.widgets.extra.text())
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            cpu_used=self.widgets.cpu_used.currentText(),
            row_mt=conversions[self.widgets.row_mt.currentText()],
            tile_rows=self.widgets.tile_rows.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            extra=self.ffmpeg_extras,
        )

        if self.mode == "CRF":
            settings.crf = int(self.widgets.crf.currentText().split(" ", 1)[0])
        else:
            settings.bitrate = self.widgets.bitrate.currentText().split(" ", 1)[0]
        return settings

    def new_source(self):
        if not self.main.streams:
            return
        if "zcale" not in self.main.flix.filters:
            self.widgets.remove_hdr.setDisabled(True)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#777}")
            self.remove_hdr_label.setToolTip("cannot remove HDR, zcale filter not in current version of FFmpeg")
            logger.warning("zcale filter not detected in current version of FFmpeg, cannot remove HDR")
        elif self.main.streams["video"][self.main.video_track].get("color_space", "").startswith("bt2020"):
            self.widgets.remove_hdr.setDisabled(False)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#000}")
        else:
            self.widgets.remove_hdr.setDisabled(True)
            self.remove_hdr_label.setStyleSheet("QLabel{color:#000}")

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
