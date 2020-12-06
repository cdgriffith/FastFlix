# -*- coding: utf-8 -*-
from box import Box
from qtpy import QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import GIFSettings
from fastflix.models.fastflix_app import FastFlixApp


class GIF(SettingPanel):
    profile_name = "gif"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, dither=None)

        grid.addLayout(self.init_dither(), 0, 0, 1, 2)
        grid.addLayout(self.init_fps(), 1, 0, 1, 2)
        grid.addLayout(self._add_custom(), 11, 0, 1, 6)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 6)
        grid.rowStretch(5)
        self.setLayout(grid)

    def init_fps(self):
        return self._add_combo_box(
            label="FPS",
            widget_name="fps",
            tooltip="Frames Per Second",
            options=[str(x) for x in range(1, 31)],
            opt="fps",
        )

    def init_dither(self):
        return self._add_combo_box(
            label="Dither",
            widget_name="dither",
            tooltip=(
                "Dither is an intentionally applied form of noise used to randomize quantization error,\n"
                "preventing large-scale patterns such as color banding in images."
            ),
            options=[
                "sierra2_4a",
                "floyd_steinberg",
                "sierra2",
                "bayer:bayer_scale=1",
                "bayer:bayer_scale=2",
                "bayer:bayer_scale=3",
                "none",
            ],
        )

    def update_video_encoder_settings(self):
        self.app.fastflix.current_video.video_settings.video_encoder_settings = GIFSettings(
            fps=int(self.widgets.fps.currentText()),
            dither=self.widgets.dither.currentText(),
            extra=self.ffmpeg_extras,
            pix_fmt="yuv420p",  # hack for thumbnails to show properly
        )

    def new_source(self):
        super().new_source()
        self.widgets.fps.setCurrentIndex(14)
        self.widgets.dither.setCurrentIndex(0)
