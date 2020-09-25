# -*- coding: utf-8 -*-
from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel


class GIF(SettingPanel):
    def __init__(self, parent, main):
        super(GIF, self).__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("GIF"), 0, 0)

        self.widgets = Box(fps=None, remove_hdr=None, dither=None)

        grid.addLayout(self.init_dither(), 0, 0, 1, 2)
        grid.addLayout(self.init_fps(), 1, 0, 1, 2)
        grid.addLayout(self._add_remove_hdr(), 2, 0, 1, 2)
        grid.addLayout(self._add_custom(), 11, 0, 1, 6)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 6)
        grid.rowStretch(5)
        self.setLayout(grid)

    def init_fps(self):
        layout = QtWidgets.QHBoxLayout()
        fps_label = QtWidgets.QLabel("FPS")
        fps_label.setToolTip("Frames Per Second")
        layout.addWidget(fps_label)
        self.widgets.fps = QtWidgets.QComboBox()
        self.widgets.fps.addItems([str(x) for x in range(1, 31)])
        self.widgets.fps.setCurrentIndex(14)
        self.widgets.fps.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.fps)
        return layout

    def init_dither(self):
        layout = QtWidgets.QHBoxLayout()
        dither_label = QtWidgets.QLabel("Dither")
        dither_label.setToolTip(
            "Dither is an intentionally applied form of noise used to randomize quantization error, <br> "
            "preventing large-scale patterns such as color banding in images."
        )
        layout.addWidget(dither_label)
        self.widgets.dither = QtWidgets.QComboBox()
        self.widgets.dither.addItems(
            [
                "sierra2_4a",
                "floyd_steinberg",
                "sierra2",
                "bayer:bayer_scale=1",
                "bayer:bayer_scale=2",
                "bayer:bayer_scale=3",
                "none",
            ]
        )
        self.widgets.dither.setCurrentIndex(0)
        self.widgets.dither.currentIndexChanged.connect(lambda: self.main.build_commands())
        layout.addWidget(self.widgets.dither)
        return layout

    def get_settings(self):
        return Box(
            fps=int(self.widgets.fps.currentText()),
            disable_hdr=bool(self.widgets.remove_hdr.currentIndex()),
            dither=self.widgets.dither.currentText(),
            extra=self.ffmpeg_extras,
            pix_fmt="yuv420p",  # hack for thumbnails to show properly
        )

    def new_source(self):
        super().new_source()
        self.widgets.fps.setCurrentIndex(14)
        self.widgets.dither.setCurrentIndex(0)
