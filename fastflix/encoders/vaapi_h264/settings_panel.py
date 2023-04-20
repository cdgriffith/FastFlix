#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import VAAPIPanel
from fastflix.language import t
from fastflix.models.encode import VAAPIH264Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

logger = logging.getLogger("fastflix")

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


class VAAPIH264(VAAPIPanel):
    profile_name = "vaapi_h264"  # must be same as profile name

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.mode = "QP"

        grid.addLayout(self.init_rc_mode(), 1, 0, 1, 2)
        # grid.addLayout(self.init_tile_rows(), 2, 0, 1, 2) # profile
        grid.addLayout(self.init_level(), 2, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 3, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 4, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        # grid.addLayout(self.init_vaapi_device(), 5, 2, 1, 1)
        # grid.addLayout(self.init_single_pass(), 5, 2, 1, 1)
        # grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        more_line = QtWidgets.QHBoxLayout()
        more_line.addLayout(self.init_vaapi_device())
        more_line.addStretch(1)
        more_line.addLayout(self.init_b_depth())
        more_line.addStretch(1)
        more_line.addLayout(self.init_async_depth())
        more_line.addStretch(1)
        more_line.addLayout(self.init_idr_interval())
        more_line.addStretch(1)
        more_line.addLayout(self.init_aud())
        more_line.addStretch(1)
        more_line.addLayout(self.init_low_power())
        grid.addLayout(more_line, 5, 0, 1, 6)

        grid.addLayout(self._add_custom(disable_both_passes=True), 10, 0, 1, 6)
        grid.setRowStretch(9, 1)
        guide_label = QtWidgets.QLabel(
            link("https://trac.ffmpeg.org/wiki/Hardware/VAAPI", t("VAAPI FFmpeg encoding"), app.fastflix.config.theme)
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, 1, 6)
        self.setLayout(grid)
        self.hide()

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        settings = VAAPIH264Settings(
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
            # extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            vaapi_device=self.widgets.vaapi_device.text(),
            low_power=self.widgets.low_power.isChecked(),
            idr_interval=self.widgets.idr_interval.text(),
            b_depth=self.widgets.b_depth.text(),
            async_depth=self.widgets.async_depth.currentText(),
            aud=self.widgets.aud.isChecked(),
            level=None if self.widgets.level.currentIndex() == 0 else self.widgets.level.currentText(),
            rc_mode=self.widgets.rc_mode.currentText(),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()