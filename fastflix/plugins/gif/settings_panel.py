# -*- coding: utf-8 -*-
from box import Box

from qtpy import QtWidgets, QtCore, QtGui


class GIF(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(GIF, self).__init__(parent)
        self.main = main

        grid = QtWidgets.QGridLayout()

        # grid.addWidget(QtWidgets.QLabel("GIF"), 0, 0)

        self.widgets = Box(fps=None, remove_hdr=None, dither=None)

        grid.addLayout(self.init_fps(), 1, 0)
        grid.addLayout(self.init_remove_hdr(), 2, 0)
        grid.addLayout(self.init_dither(), 0, 0)

        grid.addWidget(QtWidgets.QWidget(), 5, 0, 5, 2)
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

    def init_remove_hdr(self):
        layout = QtWidgets.QHBoxLayout()
        remove_hdr_level = QtWidgets.QLabel("Remove HDR")
        remove_hdr_level.setToolTip(
            "Convert BT2020 colorspace into bt709\n " "WARNING: This will take much longer and result in a larger file"
        )
        layout.addWidget(remove_hdr_level)
        self.widgets.remove_hdr = QtWidgets.QComboBox()
        self.widgets.remove_hdr.addItems(["No", "Yes"])
        self.widgets.remove_hdr.setCurrentIndex(0)
        self.widgets.remove_hdr.setDisabled(True)
        self.widgets.remove_hdr.currentIndexChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.remove_hdr)
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
        )

    def new_source(self):
        if not self.main.streams:
            return
        if self.main.streams["video"][self.main.video_track].get("color_space", "").startswith("bt2020"):
            self.widgets.remove_hdr.setDisabled(False)
            self.widgets.dither.setCurrentIndex(1)
        else:
            self.widgets.dither.setCurrentIndex(0)
            self.widgets.remove_hdr.setDisabled(True)
        self.widgets.fps.setCurrentIndex(14)
        self.widgets.dither.setCurrentIndex(0)
