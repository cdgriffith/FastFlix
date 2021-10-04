# -*- coding: utf-8 -*-
from box import Box
from PySide6 import QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import WebPSettings
from fastflix.models.fastflix_app import FastFlixApp


class WEBP(SettingPanel):
    profile_name = "webp"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

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
        return self._add_combo_box(label="lossless", options=["yes", "no"], widget_name="lossless", default=1)

    def init_compression(self):
        return self._add_combo_box(
            label="compression level",
            options=["0", "1", "2", "3", "4", "5", "6"],
            widget_name="compression",
            tooltip="For lossy, this is a quality/speed tradeoff.\nFor lossless, this is a size/speed tradeoff.",
            default=4,
        )

    def init_preset(self):
        return self._add_combo_box(
            label="preset",
            options=["none", "default", "picture", "photo", "drawing", "icon", "text"],
            widget_name="preset",
            default=1,
        )

    def init_modes(self):
        layout = QtWidgets.QGridLayout()
        qscale_group_box = QtWidgets.QGroupBox()
        qscale_group_box.setStyleSheet("QGroupBox{padding-top:5px; margin-top:-18px}")
        qscale_box_layout = QtWidgets.QHBoxLayout()

        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)

        qscale_radio = QtWidgets.QRadioButton("qscale")
        qscale_radio.setChecked(True)
        qscale_radio.setFixedWidth(80)
        self.widgets.mode.addButton(qscale_radio)

        self.widgets.qscale = QtWidgets.QComboBox()
        self.widgets.qscale.setFixedWidth(250)
        self.widgets.qscale.addItems([str(x) for x in range(0, 101, 5)] + ["Custom"])
        self.widgets.qscale.setCurrentIndex(15)
        self.widgets.qscale.currentIndexChanged.connect(lambda: self.mode_update())
        self.widgets.custom_qscale = QtWidgets.QLineEdit("75")
        self.widgets.custom_qscale.setFixedWidth(100)
        self.widgets.custom_qscale.setDisabled(True)
        self.widgets.custom_qscale.setValidator(self.only_int)
        self.widgets.custom_qscale.textChanged.connect(lambda: self.main.build_commands())
        qscale_box_layout.addWidget(qscale_radio)
        qscale_box_layout.addWidget(self.widgets.qscale)
        qscale_box_layout.addStretch()
        qscale_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
        qscale_box_layout.addWidget(self.widgets.custom_qscale)

        qscale_group_box.setLayout(qscale_box_layout)

        layout.addWidget(qscale_group_box, 0, 0)
        return layout

    def update_video_encoder_settings(self):
        lossless = self.widgets.lossless.currentText()

        settings = WebPSettings(
            lossless="1" if lossless == "yes" else "0",
            compression=self.widgets.compression.currentText(),
            preset=self.widgets.preset.currentText(),
            extra=self.ffmpeg_extras,
            pix_fmt="yuv420p",  # hack for thumbnails to show properly
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
        )
        qscale = self.widgets.qscale.currentText()
        if self.widgets.custom_qscale.isEnabled():
            if not self.widgets.custom_qscale.text():
                settings.qscale = 75
            else:
                settings.qscale = int(self.widgets.custom_qscale.text())
        else:
            settings.qscale = int(qscale.split(" ", 1)[0])
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def new_source(self):
        super().new_source()
        self.widgets.lossless.setCurrentIndex(0)

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()

    def mode_update(self):
        self.widgets.custom_qscale.setDisabled(self.widgets.qscale.currentText() != "Custom")
        self.main.build_commands()
