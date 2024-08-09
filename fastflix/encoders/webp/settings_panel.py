# -*- coding: utf-8 -*-
from box import Box
from PySide6 import QtWidgets
import logging

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import WebPSettings
from fastflix.models.fastflix_app import FastFlixApp


logger = logging.getLogger("fastflix")


class WEBP(SettingPanel):
    profile_name = "webp"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app
        self.mode = "qscale"

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, dither=None)

        grid.addLayout(self.init_lossless(), 0, 0, 1, 2)
        grid.addLayout(self.init_compression(), 1, 0, 1, 2)
        grid.addLayout(self.init_preset(), 2, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 2, 4)

        grid.addLayout(self._add_custom(disable_both_passes=True), 11, 0, 1, 6)
        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 6)
        grid.rowStretch(5)
        self.setLayout(grid)

    def init_lossless(self):
        return self._add_combo_box(
            label="lossless",
            options=["yes", "no"],
            widget_name="lossless",
            default="yes",
            opt="lossless",
        )

    def init_compression(self):
        return self._add_combo_box(
            label="compression level",
            options=["0", "1", "2", "3", "4", "5", "6"],
            widget_name="compression",
            tooltip="For lossy, this is a quality/speed tradeoff.\nFor lossless, this is a size/speed tradeoff.",
            default=4,
            opt="compression",
        )

    def init_preset(self):
        return self._add_combo_box(
            label="preset",
            options=["none", "default", "picture", "photo", "drawing", "icon", "text"],
            widget_name="preset",
            default=1,
            opt="preset",
        )

    def init_modes(self):
        return self._add_modes(
            qp_name="qscale",
            add_qp=True,
            disable_bitrate=True,
            recommended_qps=[str(x) for x in range(0, 101, 5)] + ["Custom"],
            recommended_bitrates=[],
        )

    def update_video_encoder_settings(self):
        settings = WebPSettings(
            lossless=self.widgets.lossless.currentText(),
            compression=self.widgets.compression.currentText(),
            preset=self.widgets.preset.currentText(),
            extra=self.ffmpeg_extras,
            pix_fmt="yuv420p",  # hack for thumbnails to show properly
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
        )
        _, settings.qscale = self.get_mode_settings()
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def new_source(self):
        super().new_source()

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()

    def mode_update(self):
        self.widgets.custom_qscale.setDisabled(self.widgets.qscale.currentText() != "Custom")
        self.main.build_commands()
