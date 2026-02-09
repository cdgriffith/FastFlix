# -*- coding: utf-8 -*-
from box import Box
from PySide6 import QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import GifskiSettings
from fastflix.models.fastflix_app import FastFlixApp


class Gifski(SettingPanel):
    profile_name = "gifski"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()
        self.widgets = Box(fps=None, quality=None)

        grid.addLayout(self.init_fps(), 0, 0, 1, 2)
        grid.addLayout(self.init_quality(), 1, 0, 1, 2)
        grid.addLayout(self.init_lossy_quality(), 2, 0, 1, 2)
        grid.addLayout(self.init_motion_quality(), 3, 0, 1, 2)
        grid.addLayout(self.init_fast(), 4, 0, 1, 2)
        grid.addLayout(self._add_custom(disable_both_passes=True), 11, 0, 1, 6)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 6)
        grid.rowStretch(5)
        self.setLayout(grid)

    def init_fps(self):
        return self._add_combo_box(
            label="FPS",
            widget_name="fps",
            tooltip="Frames Per Second",
            options=[str(x) for x in range(1, 51)],
            opt="fps",
        )

    def init_quality(self):
        return self._add_combo_box(
            label="Quality",
            widget_name="quality",
            tooltip="Overall quality (1-100, higher is better quality but larger file size)",
            options=[str(x) for x in range(1, 101)],
            default=89,
            opt="quality",
        )

    def init_lossy_quality(self):
        return self._add_combo_box(
            label="Lossy Quality",
            widget_name="lossy_quality",
            tooltip="Lower values reduce file size at cost of more noise/grain (1-100, or auto to let gifski decide)",
            options=["auto"] + [str(x) for x in range(1, 101)],
            opt="lossy_quality",
        )

    def init_motion_quality(self):
        return self._add_combo_box(
            label="Motion Quality",
            widget_name="motion_quality",
            tooltip="Lower values reduce file size for animations with motion (1-100, or auto to let gifski decide)",
            options=["auto"] + [str(x) for x in range(1, 101)],
            opt="motion_quality",
        )

    def init_fast(self):
        return self._add_check_box(
            label="Fast Mode",
            widget_name="fast",
            tooltip="Encode faster at cost of quality",
            opt="fast",
        )

    def update_video_encoder_settings(self):
        self.app.fastflix.current_video.video_settings.video_encoder_settings = GifskiSettings(
            fps=self.widgets.fps.currentText(),
            quality=self.widgets.quality.currentText(),
            lossy_quality=self.widgets.lossy_quality.currentText(),
            motion_quality=self.widgets.motion_quality.currentText(),
            fast=self.widgets.fast.isChecked(),
            extra=self.ffmpeg_extras,
            pix_fmt="yuv420p",
        )

    def new_source(self):
        super().new_source()
