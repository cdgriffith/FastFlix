# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k   (320x240p @ 24,25,30)",
    "276k   (640x360p @ 24,25,30)",
    "512k   (640x480p @ 24,25,30)",
    "1024k  (1280x720p @ 24,25,30)",
    "1800k (1280x720p @ 50,60)",
    "1800k (1920x1080p @ 24,25,30)",
    "3000k (1920x1080p @ 50,60)",
    "6000k (2560x1440p @ 24,25,30)",
    "9000k (2560x1440p @ 50,60)",
    "12000k (3840x2160p @ 24,25,30)",
    "18000k (3840x2160p @ 50,60)",
    "Custom",
]

recommended_crfs = [
    "37 (240p)",
    "36 (360p)",
    "33 (480p)",
    "32 (720p)",
    "31 (1080p)",
    "24 (1440p)",
    "15 (2160p)",
    "Custom",
]

pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]


class VP9(SettingPanel):
    def __init__(self, parent, main):
        super(VP9, self).__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("VP9"), 0, 0)

        self.widgets = Box(fps=None, remove_hdr=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self._add_remove_hdr(), 2, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 6, 4)
        grid.addLayout(self.init_single_pass(), 6, 2, 1, 2)

        grid.addLayout(self.init_quality(), 1, 0, 1, 2)
        grid.addLayout(self.init_speed(), 0, 0, 1, 2)

        grid.addLayout(self.init_row_mt(), 4, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 5, 0, 1, 2)

        grid.addLayout(self.init_max_mux(), 6, 0, 1, 2)
        grid.addLayout(self._add_custom(), 9, 0, 1, 6)

        grid.addWidget(QtWidgets.QWidget(), 8, 0)
        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            f"<a href='https://trac.ffmpeg.org/wiki/Encode/VP9'>FFMPEG VP9 Encoding Guide</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 10, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            default=1,
        )

    def init_quality(self):
        layout = QtWidgets.QHBoxLayout()
        quality_level = QtWidgets.QLabel("Quality")
        quality_level.setToolTip(
            "good is the default and recommended for most applications <br> "
            "best is recommended if you have lots of time and want the best compression efficiency."
        )
        layout.addWidget(quality_level)
        self.widgets.quality = QtWidgets.QComboBox()
        self.widgets.quality.addItems(["realtime", "good", "best"])
        self.widgets.quality.setCurrentIndex(1)
        self.widgets.quality.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.quality)
        return layout

    def init_speed(self):
        layout = QtWidgets.QHBoxLayout()
        speed_level = QtWidgets.QLabel("Speed")
        speed_level.setToolTip(
            "Using 1 or 2 will increase encoding speed at the expense of having some impact on "
            "quality and rate control accuracy.<br> 4 or 5 will turn off rate distortion optimization, "
            "having even more of an impact on quality."
        )
        layout.addWidget(speed_level)
        self.widgets.speed = QtWidgets.QComboBox()
        self.widgets.speed.addItems([str(x) for x in range(6)])
        self.widgets.speed.setCurrentIndex(0)
        self.widgets.speed.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.speed)
        return layout

    def init_row_mt(self):
        layout = QtWidgets.QHBoxLayout()
        row_mt_label = QtWidgets.QLabel("Row multithreading")
        row_mt_label.setToolTip(
            "This improves encoding speed significantly on systems that "
            "are otherwise underutilised when encoding VP9."
        )
        layout.addWidget(row_mt_label)
        self.widgets.row_mt = QtWidgets.QCheckBox()
        self.widgets.row_mt.setChecked(False)
        self.widgets.row_mt.toggled.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.row_mt)
        return layout

    def init_single_pass(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Single Pass (CRF)"))
        self.widgets.single_pass = QtWidgets.QCheckBox()
        self.widgets.single_pass.setChecked(False)
        self.widgets.single_pass.toggled.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.single_pass)
        return layout

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
        crf_group_box = QtWidgets.QGroupBox()
        crf_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        crf_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        # rotation_dir = Path(base_path, 'data', 'rotations')
        # group_box.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-15px; padding-bottom:-5px}")
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

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

        crf_radio = QtWidgets.QRadioButton("CRF")
        crf_radio.setChecked(True)
        crf_radio.setFixedWidth(80)
        self.widgets.mode.addButton(crf_radio)

        self.widgets.crf = QtWidgets.QComboBox()
        self.widgets.crf.setFixedWidth(250)
        self.widgets.crf.addItems(recommended_crfs)
        self.widgets.crf.setCurrentIndex(4)
        self.widgets.crf.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_crf = QtWidgets.QLineEdit("30")
        self.widgets.custom_crf.setFixedWidth(100)
        self.widgets.custom_crf.setDisabled(True)
        self.widgets.custom_crf.setValidator(self.only_int)
        self.widgets.custom_crf.textChanged.connect(lambda: self.main.build_commands())
        crf_box_layout.addWidget(crf_radio)
        crf_box_layout.addWidget(self.widgets.crf)
        crf_box_layout.addStretch()
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
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            quality=self.widgets.quality.currentText(),
            speed=self.widgets.speed.currentText(),
            row_mt=int(self.widgets.row_mt.isChecked()),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            single_pass=self.widgets.single_pass.isChecked(),
            max_mux=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
        )
        if self.mode == "CRF":
            crf = self.widgets.crf.currentText()
            settings.crf = int(crf.split(" ", 1)[0]) if crf.lower() != "custom" else self.widgets.custom_crf.text()
        else:
            bitrate = self.widgets.bitrate.currentText()
            if bitrate.lower() == "custom":
                settings.bitrate = self.widgets.custom_bitrate.text()
            else:
                settings.bitrate = bitrate.split(" ", 1)[0]
        return settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
