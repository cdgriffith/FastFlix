#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from pathlib import Path

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.fastflix_app import FastFlixApp

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
    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.mode = "CRF"
        self.updating_settings = False

        grid.addLayout(self.init_preset(), 1, 0, 1, 1)
        grid.addLayout(self._add_remove_hdr(connect=lambda: self.setting_change()), 2, 0, 1, 1)
        grid.addLayout(self.init_intra_encoding(), 3, 0, 1, 1)
        grid.addLayout(self.init_max_mux(), 4, 0, 1, 1)
        grid.addLayout(self.init_tune(), 5, 0, 1, 1)
        grid.addLayout(self.init_pix_fmt(), 6, 0, 1, 1)
        grid.addLayout(self.init_profile(), 7, 0, 1, 1)

        grid.addLayout(self.init_modes(), 0, 1, 5, 5)
        grid.addLayout(self.init_hdr10(), 5, 1, 1, 1)
        grid.addLayout(self.init_hdr10_opt(), 5, 2, 1, 1)
        grid.addLayout(self.init_repeat_headers(), 5, 3, 1, 1)
        grid.addLayout(self.init_aq_mode(), 5, 4, 1, 2)
        grid.addLayout(self.init_x265_params(), 6, 1, 1, 5)

        grid.addLayout(self.init_dhdr10_info(), 7, 1, 1, 4)
        grid.addWidget(self.init_dhdr10_warning(), 7, 5, 1, 4)

        grid.setRowStretch(9, True)

        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        guide_label = QtWidgets.QLabel(
            "<a href='https://trac.ffmpeg.org/wiki/Encode/H.265'>FFMPEG HEVC / H.265 Encoding Guide</a>"
            " | <a href='https://codecalamity.com/encoding-uhd-4k-hdr10-videos-with-ffmpeg/'>"
            "CodeCalamity UHD HDR Encoding Guide</a>"
            " | <a href='https://github.com/cdgriffith/FastFlix/wiki/HDR10-Plus-Metadata-Extraction'>"
            "HDR10+ Metadata Extraction"
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)

        self.setLayout(grid)
        self.hide()

    def init_dhdr10_info(self):
        return self._add_file_select(
            label="HDR10+ Metadata",
            widget_name="hdr10plus_metadata",
            button_action=lambda: self.dhdr10_update(),
            tooltip="dhdr10_info: Path to HDR10+ JSON metadata file",
        )

    def init_dhdr10_warning(self):
        label = QtWidgets.QLabel()
        label.setToolTip(
            "WARNING: This only works on a few FFmpeg builds, and it will not raise error on failure!\n"
            "Specifically, FFmpeg needs the x265 ENABLE_HDR10_PLUS option enabled on compile.\n"
            "The latest windows builds from BtbN should have this feature.\n"
            "I do not know of any public Linux/Mac ones that do."
        )
        icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        label.setPixmap(icon.pixmap(16))
        # label.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        return label

    def init_hdr10(self):
        return self._add_check_box(
            label="Force HDR10 signaling",
            widget_name="hdr10",
            tooltip=(
                "hdr10: Force signaling of HDR10 parameters in SEI packets.\n"
                " Enabled automatically when --master-display or --max-cll is specified.\n"
                " Useful when there is a desire to signal 0 values for max-cll and max-fall.\n"
                " Default disabled."
            ),
            opt="x265_hdr10_signaling",
        )

    def init_hdr10_opt(self):
        return self._add_check_box(
            label="| HDR10 Optimizations",
            widget_name="hdr10_opt",
            tooltip=(
                "hdr10-opt: Enable block-level luma and chroma QP optimization for HDR10 content.\n"
                "It is recommended that AQ-mode be enabled along with this feature"
            ),
            opt="x265_hdr10_opt",
        )

    def init_repeat_headers(self):
        return self._add_check_box(
            label="| Repeat Headers",
            widget_name="repeat_headers",
            tooltip=(
                "repeat-headers: If enabled, x265 will emit VPS, SPS, and PPS headers with every keyframe.\n"
                "This is intended for use when you do not have a container to keep the stream headers for you\n"
                " and you want keyframes to be random access points."
            ),
            opt="x265_repeat_headers",
        )

    def init_aq_mode(self):
        return self._add_combo_box(
            label="| Adaptive Quantization",
            widget_name="aq_mode",
            options=[
                "disabled",
                "enabled",
                "enabled + auto-variance",
                "enabled + av + dark bias",
                "enabled + av + edge",
            ],
            tooltip=(
                "aq-mode: Adaptive Quantization operating mode.\n"
                "Raise or lower per-block quantization based on complexity analysis of the source image.\n"
                "The more complex the block, the more quantization is used.\n"
                "Default: AQ enabled with auto-variance"
            ),
            opt="x265_aq",
        )

    def init_intra_encoding(self):
        return self._add_combo_box(
            label="Intra-encoding",
            widget_name="intra_encoding",
            options=["No", "Yes"],
            tooltip=(
                "keyint: Enable Intra-Encoding by forcing keyframes every 1 second (Blu-ray spec)\n"
                "This option is not recommenced unless you need to conform "
                "to Blu-ray standards to burn to a physical disk"
            ),
            opt="x265_intra_encoding",
        )

    def init_preset(self):
        return self._add_combo_box(
            label="Preset",
            widget_name="preset",
            options=[
                "ultrafast",
                "superfast",
                "veryfast",
                "faster",
                "fast",
                "medium",
                "slow",
                "slower",
                "veryslow",
                "placebo",
            ],
            tooltip=(
                "preset: The slower the preset, the better the compression and quality\n"
                "Slow is highest personal recommenced, as past that is much smaller gains"
            ),
            connect="default",
            opt="x265_preset",
        )

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            widget_name="tune",
            options=["default", "psnr", "ssim", "grain", "zerolatency", "fastdecode", "animation"],
            tooltip="tune: Tune the settings for a particular type of source or situation",
            connect="default",
            opt="x265_tune",
        )

    def init_profile(self):
        return self._add_combo_box(
            label="Profile",
            tooltip="profile: Enforce an encode profile",
            widget_name="profile",
            options=["default", "main", "main10", "mainstillpicture"],
            opt="x265_profile",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            connect=lambda: self.setting_change(pix_change=True),
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip=(
                "max_muxing_queue_size: " 'Useful when you have the "Too many packets buffered for output stream" error'
            ),
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

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

    def init_x265_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.x265_params = QtWidgets.QLabel("Additional x265 params")
        tool_tip = (
            "Extra x265 params in opt=1:opt2=0 format,\n"
            "cannot modify generated settings\n"
            "examples: level-idc=4.1:rc-lookahead=10 "
        )
        self.labels.x265_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.x265_params)
        self.widgets.x265_params = QtWidgets.QLineEdit()
        self.widgets.x265_params.setToolTip(tool_tip)
        self.widgets.x265_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.x265_params)
        return layout

    def dhdr10_update(self):
        dirname = Path(self.widgets.hdr10plus_metadata.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="hdr10_metadata", directory=str(dirname), filter="HDR10+ Metadata (*.json)"
        )
        if not filename or not filename[0]:
            return
        self.widgets.hdr10plus_metadata.setText(filename[0])
        self.main.page_update()

    def setting_change(self, update=True, pix_change=False):
        if self.updating_settings or not self.main.input_video:
            return
        self.updating_settings = True
        if pix_change:
            if self.widgets.pix_fmt.currentText().startswith("8-bit"):
                self.widgets.hdr10_opt.setDisabled(True)
                self.widgets.hdr10_opt.setChecked(False)
                self.widgets.hdr10.setDisabled(True)
                self.widgets.hdr10.setChecked(False)
            else:
                self.widgets.hdr10.setDisabled(False)
                self.widgets.hdr10.setChecked(True)
                self.widgets.hdr10_opt.setDisabled(False)
            self.main.page_update()
            self.updating_settings = False
            return

        remove_hdr = self.widgets.remove_hdr.currentIndex()
        bit_depth = self.main.streams["video"][self.main.video_track].bit_depth
        if remove_hdr == 1:
            self.widgets.pix_fmt.clear()
            self.widgets.pix_fmt.addItems([pix_fmts[0]])
            self.widgets.pix_fmt.setCurrentIndex(0)
            self.widgets.hdr10_opt.setDisabled(True)
            self.widgets.hdr10_opt.setChecked(False)
            self.widgets.hdr10.setDisabled(True)
            self.widgets.hdr10.setChecked(False)
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
            if not self.widgets.pix_fmt.currentText().startswith("8-bit"):
                self.widgets.hdr10_opt.setDisabled(False)
                self.widgets.hdr10.setDisabled(False)
                self.widgets.hdr10.setChecked(True)
        if update:
            self.main.page_update()
        self.updating_settings = False

    def new_source(self):
        super().new_source()
        self.setting_change()

    def get_settings(self):
        settings = Box(
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            preset=self.widgets.preset.currentText(),
            intra_encoding=bool(self.widgets.intra_encoding.currentIndex()),
            max_mux=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            profile=self.widgets.profile.currentText(),
            hdr10_opt=self.widgets.hdr10_opt.isChecked(),
            repeat_headers=self.widgets.repeat_headers.isChecked(),
            aq_mode=self.widgets.aq_mode.currentIndex(),
            hdr10plus_metadata=self.widgets.hdr10plus_metadata.text().strip().replace("\\", "/"),
            extra=self.ffmpeg_extras,
        )

        x265_params_text = self.widgets.x265_params.text().strip()
        settings.x265_params = x265_params_text.split(":") if x265_params_text else []

        tune = self.widgets.tune.currentText()
        settings.tune = tune if tune.lower() != "default" else None

        if self.mode == "CRF":
            crf = self.widgets.crf.currentText()
            settings.crf = int(crf.split(" ", 1)[0]) if crf != "Custom" else int(self.widgets.custom_crf.text())
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
