#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import SVTAVIFSettings
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
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
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


class SVT_AV1_AVIF(SettingPanel):
    profile_name = "svt_av1_avif"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None, segment_size=None)

        self.mode = "QP"

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 1, 0, 1, 2)
        grid.addLayout(self.init_qp_or_crf(), 5, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self.init_svtav1_params(), 5, 2, 1, 4)

        grid.setRowStretch(8, 1)
        guide_label = QtWidgets.QLabel(
            link(
                "https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/Ffmpeg.md",
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

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_preset(self):
        return self._add_combo_box(
            label="Preset",
            widget_name="speed",
            options=[str(x) for x in range(14)],
            tooltip="Quality/Speed ratio modifier",
            opt="speed",
        )

    def init_qp_or_crf(self):
        return self._add_combo_box(
            label="Quantization Mode",
            widget_name="qp_mode",
            options=["qp", "crf"],
            tooltip="Use CRF or QP",
            opt="qp_mode",
        )

    def init_svtav1_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.svtav1_params = QtWidgets.QLabel(t("Additional svt av1 params"))
        self.labels.svtav1_params.setFixedWidth(200)
        tool_tip = f"{t('Extra svt av1 params in opt=1:opt2=0 format')},\n" f"{t('cannot modify generated settings')}"
        self.labels.svtav1_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.svtav1_params)
        self.widgets.svtav1_params = QtWidgets.QLineEdit()
        self.widgets.svtav1_params.setToolTip(tool_tip)
        self.widgets.svtav1_params.setText(
            ":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "svtav1_params"))
        )
        self.opts["svtav1_params"] = "svtav1_params"
        self.widgets.svtav1_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.svtav1_params)
        return layout

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_qp, qp_name="qp")

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        svtav1_params_text = self.widgets.svtav1_params.text().strip()

        settings = SVTAVIFSettings(
            speed=self.widgets.speed.currentText(),
            qp_mode=self.widgets.qp_mode.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
            svtav1_params=svtav1_params_text.split(":") if svtav1_params_text else [],
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
