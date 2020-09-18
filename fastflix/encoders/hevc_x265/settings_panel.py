#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k     (320x240p @ 30fps)",
    "276k     (640x360p @ 30fps)",
    "512k     (640x480p @ 30fps)",
    "1024k   (1280x720p @ 30fps)",
    "1800k   (1280x720p @ 60fps)",
    "1800k   (1920x1080p @ 30fps)",
    "3000k   (1920x1080p @ 60fps)",
    "6000k   (2560x1440p @ 30fps)",
    "9000k   (2560x1440p @ 60fps)",
    "12000k (3840x2160p @ 30fps)",
    "18000k (3840x2160p @ 60fps)",
    "Custom",
]

recommended_crfs = [
    "28 (x265 default - lower quality)",
    "27",
    "26",
    "25",
    "24 (480p)",
    "23 (720p)",
    "22 (1080p)",
    "21 (1440p)",
    "20 (2160p)",
    "19",
    "18 (very high quality)",
    "Custom",
]

pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le", "12-bit: yuv420p12le"]


class HEVC(SettingPanel):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(remove_hdr=None, mode=None, intra_encoding=None)

        self.mode = "CRF"
        self.updating_settings = False

        grid.addLayout(self.init_modes(), 0, 2, 6, 4)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.addLayout(self.init_preset(), 1, 0, 1, 2)
        grid.addLayout(self.init_remove_hdr(), 2, 0, 1, 2)
        grid.addLayout(self.init_intra_encoding(), 3, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 4, 0, 1, 2)
        grid.addLayout(self.init_tune(), 5, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 6, 0, 1, 2)
        grid.addLayout(self.init_profile(), 7, 0, 1, 2)

        grid.setRowStretch(9, 1)

        guide_label = QtWidgets.QLabel(
            "<a href='https://trac.ffmpeg.org/wiki/Encode/H.265'>FFMPEG HEVC / H.265 Encoding Guide</a>"
            " | <a href='https://codecalamity.com/encoding-uhd-4k-hdr10-videos-with-ffmpeg/'>"
            "CodeCalamity UHD HDR Encoding Guide</a>"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)

        self.setLayout(grid)
        self.hide()

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
        self.widgets.remove_hdr.currentIndexChanged.connect(lambda: self.setting_change())
        layout.addWidget(self.widgets.remove_hdr)
        return layout

    def init_intra_encoding(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Intra-encoding")
        label.setToolTip(
            "Enable Intra-Encoding by forcing keyframes every 1 second (Blu-ray spec)\n"
            "This option is not recommenced unless you need to conform to Blu-ray standards to burn to a physical disk"
        )
        layout.addWidget(label)
        self.widgets.intra_encoding = QtWidgets.QComboBox()
        self.widgets.intra_encoding.addItems(["No", "Yes"])
        self.widgets.intra_encoding.setCurrentIndex(0)
        self.widgets.intra_encoding.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.intra_encoding)
        return layout

    def init_preset(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Preset")
        label.setToolTip(
            "The slower the preset, the better the compression and quality\n"
            "Slow is highest personal recommenced, as past that is much smaller gains"
        )
        layout.addWidget(label)
        self.widgets.preset = QtWidgets.QComboBox()
        self.widgets.preset.addItems(
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"]
        )
        self.widgets.preset.setCurrentIndex(5)
        self.widgets.preset.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.preset)
        return layout

    def init_tune(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Tune")
        label.setToolTip("Tune the settings for a particular type of source or situation")
        layout.addWidget(label)
        self.widgets.tune = QtWidgets.QComboBox()
        self.widgets.tune.addItems(["default", "psnr", "ssim", "grain", "zerolatency", "fastdecode", "animation"])
        self.widgets.tune.setCurrentIndex(0)
        self.widgets.tune.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.tune)
        return layout

    def init_profile(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Profile")
        label.setToolTip("Enforce an encode profile")
        layout.addWidget(label)
        self.widgets.profile = QtWidgets.QComboBox()
        self.widgets.profile.addItems(["default", "main", "main10", "mainstillpicture"])
        self.widgets.profile.setCurrentIndex(0)
        self.widgets.profile.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.profile)
        return layout

    def init_pix_fmt(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Bit Depth")
        label.setToolTip("Pixel Format (requires at least 10-bit for HDR)")
        layout.addWidget(label)
        self.widgets.pix_fmt = QtWidgets.QComboBox()
        self.widgets.pix_fmt.addItems(pix_fmts)
        self.widgets.pix_fmt.setCurrentIndex(1)
        self.widgets.pix_fmt.currentIndexChanged.connect(lambda: self.setting_change(pix_change=True))
        layout.addWidget(self.widgets.pix_fmt)
        return layout

    def init_max_mux(self):
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Max Muxing Queue Size")
        label.setToolTip('Only change this if you are getting the error "Too many packets buffered for output stream"')
        layout.addWidget(label)
        self.widgets.max_mux = QtWidgets.QComboBox()
        self.widgets.max_mux.addItems(["default", "1024", "2048", "4096", "8192"])
        self.widgets.max_mux.setCurrentIndex(0)
        self.widgets.max_mux.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.max_mux)
        return layout

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        crf_group_box = QtWidgets.QGroupBox()
        crf_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        crf_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        bitrate_box_layout = QtWidgets.QHBoxLayout()
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

        crf_help = (
            "CRF is extremely source dependant,<br>"
            "the resolution-to-crf are mere suggestions!<br><br>"
            "Quality also depends on encoding speed.<br> "
            "For example, SLOW CRF 22 will have a result near FAST CRF 20."
        )
        crf_radio = QtWidgets.QRadioButton("CRF")
        crf_radio.setChecked(True)
        crf_radio.setFixedWidth(80)
        crf_radio.setToolTip(crf_help)
        self.widgets.mode.addButton(crf_radio)

        self.widgets.crf = QtWidgets.QComboBox()
        self.widgets.crf.setToolTip(crf_help)
        self.widgets.crf.setFixedWidth(250)
        self.widgets.crf.addItems(recommended_crfs)
        self.widgets.crf.setCurrentIndex(0)
        self.widgets.crf.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_crf = QtWidgets.QLineEdit("30")
        self.widgets.custom_crf.setFixedWidth(100)
        self.widgets.custom_crf.setDisabled(True)
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

    def setting_change(self, update=True, pix_change=False):
        if self.updating_settings:
            return
        if pix_change:
            self.main.page_update()
            return
        self.updating_settings = True
        remove_hdr = bool(self.widgets.remove_hdr.currentIndex())
        bit_depth = self.main.streams["video"][self.main.video_track].bit_depth

        if remove_hdr:
            self.widgets.pix_fmt.clear()
            self.widgets.pix_fmt.addItems([pix_fmts[0:1]])
            self.widgets.pix_fmt.setCurrentIndex(0)
        else:
            self.widgets.pix_fmt.clear()
            if bit_depth == 12:
                self.widgets.pix_fmt.addItems(pix_fmts[2:])
                self.widgets.pix_fmt.setCurrentIndex(0)
            elif bit_depth == 10:
                self.widgets.pix_fmt.addItems(pix_fmts[1:])
                self.widgets.pix_fmt.setCurrentIndex(0)
            else:
                self.widgets.pix_fmt.addItems(pix_fmts)
                self.widgets.pix_fmt.setCurrentIndex(1)
        if update:
            self.main.page_update()
        self.updating_settings = False

    def get_settings(self):
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            preset=self.widgets.preset.currentText(),
            intra_encoding=bool(self.widgets.intra_encoding.currentIndex()),
            max_mux=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            profile=self.widgets.profile.currentText(),
            extra=self.ffmpeg_extras,
        )

        tune = self.widgets.tune.currentText()
        settings.tune = tune if tune.lower() != "default" else None

        if self.mode == "CRF":
            crf = self.widgets.crf.currentText()
            settings.crf = int(crf.split(" ", 1)[0]) if crf != "Custom" else int(self.widgets.custom_crf.text())
        else:
            bitrate = self.widgets.bitrate.currentText()
            if bitrate.lower() == "custom":
                settings.bitrate = self.widgets.custom_bitrate.currentText()
            else:
                settings.bitrate = bitrate.split(" ", 1)[0]
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
        self.setting_change(update=False)

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
