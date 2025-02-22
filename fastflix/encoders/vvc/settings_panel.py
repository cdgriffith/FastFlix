#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import VVCSettings
from fastflix.models.fastflix_app import FastFlixApp


logger = logging.getLogger("fastflix")

presets = ["faster", "fast", "medium", "slow", "slower"]

recommended_bitrates = [
    "150k     (320x240p @ 30fps)",
    "276k     (640x360p @ 30fps)",
    "512k     (640x480p @ 30fps)",
    "1500k   (1280x720p @ 30fps)",
    "2000k   (1280x720p @ 60fps)",
    "3000k   (1920x1080p @ 30fps)",
    "4000k   (1920x1080p @ 60fps)",
    "6000k   (2560x1440p @ 30fps)",
    "9000k   (2560x1440p @ 60fps)",
    "12000k (3840x2160p @ 30fps)",
    "18000k (3840x2160p @ 60fps)",
    "Custom",
]

recommended_qps = [
    "28",
    "27",
    "26",
    "25",
    "24 (480p)",
    "23 (720p)",
    "22 (1080p)",
    "21 (1440p)",
    "20 (2160p)",
    "19",
    "18",
    "17",
    "16",
    "15",
    "14 (higher quality)",
    "Custom",
]

pix_fmts = [
    "10-bit: yuv420p10le",
]


def get_breaker():
    breaker_line = QtWidgets.QWidget()
    breaker_line.setMaximumHeight(2)
    breaker_line.setStyleSheet("background-color: #ccc; margin: auto 0; padding: auto 0;")
    return breaker_line


class VVC(SettingPanel):
    profile_name = "vvc"
    hdr10plus_signal = QtCore.Signal(str)
    hdr10plus_ffmpeg_signal = QtCore.Signal(str)

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.mode = "QP"
        self.updating_settings = False
        self.extract_thread = None

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_tier(), 1, 0, 1, 2)
        grid.addLayout(self.init_levels(), 2, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 3, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        breaker = QtWidgets.QHBoxLayout()
        breaker_label = QtWidgets.QLabel(t("Advanced"))

        breaker.addWidget(get_breaker(), stretch=1)
        breaker.addWidget(breaker_label, alignment=QtCore.Qt.AlignHCenter)
        breaker.addWidget(get_breaker(), stretch=1)

        grid.addLayout(breaker, 5, 0, 1, 6)

        grid.addLayout(self.init_max_mux(), 8, 0, 1, 2)

        grid.addLayout(self.init_vvc_params(), 8, 2, 1, 4)

        self.ffmpeg_level = QtWidgets.QLabel()
        grid.addWidget(self.ffmpeg_level, 10, 2, 1, 4)

        grid.setRowStretch(11, True)

        grid.addLayout(self._add_custom(), 12, 0, 1, 6)

        self.setLayout(grid)
        self.hide()

    def init_tier(self):
        return self._add_combo_box(
            label="Tier",
            tooltip="Set the encoding tier",
            widget_name="tier",
            options=["main", "high"],
            opt="tier",
        )

    def init_levels(self):
        # https://github.com/fraunhoferhhi/vvenc/blob/cf8ba5ed74f8e8c7c9e7b6f81f7fb08bce6241b0/source/Lib/vvenc/vvencCfg.cpp#L159
        return self._add_combo_box(
            label="IDC Level",
            tooltip="Set the IDC level",
            widget_name="levelidc",
            options=[
                t("Auto"),
                "1",
                "2",
                "2.1",
                "3",
                "3.1",
                "4",
                "4.1",
                "5",
                "5.1",
                "5.2",
                "6",
                "6.1",
                "6.2",
                "6.3",
                "15.5",
            ],
            opt="levelidc",
        )

    def init_preset(self):
        layout = self._add_combo_box(
            label="Preset",
            widget_name="preset",
            options=presets,
            tooltip=(
                "preset: The slower the preset, the better the compression and quality\n"
                "Slow is the slowest preset personally recommended,\n"
                "presets slower than this result in much smaller gains"
            ),
            connect="default",
            opt="preset",
        )
        return layout

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            connect=lambda: self.setting_change(pix_change=True),
            opt="pix_fmt",
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='max_muxing_queue_size: Raise to fix "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_qps, qp_name="qp")

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def init_vvc_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.vvc_params = QtWidgets.QLabel(t("Additional vvc params"))
        self.labels.vvc_params.setFixedWidth(200)
        tool_tip = (
            f"{t('Extra vvc params in opt=1:opt2=0 format')},\n"
            f"{t('cannot modify generated settings')}\n"
            f"{t('examples: level-idc=4.1:rc-lookahead=10')} \n"
        )
        self.labels.vvc_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.vvc_params)
        self.widgets.vvc_params = QtWidgets.QLineEdit()
        self.widgets.vvc_params.setToolTip(tool_tip)
        self.widgets.vvc_params.setText(":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "vvc_params")))
        self.opts["vvc_params"] = "vvc_params"
        self.widgets.vvc_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.vvc_params)
        return layout

    def setting_change(self, update=True, pix_change=False):
        if self.updating_settings or not self.main.input_video:
            return
        self.updating_settings = True

        if update:
            self.main.page_update()
        self.updating_settings = False

    def new_source(self):
        if not self.app.fastflix.current_video:
            return
        super().new_source()
        self.setting_change()
        if self.extract_thread:
            try:
                self.extract_thread.terminate()
            except Exception:
                pass

    def update_video_encoder_settings(self):
        if not self.app.fastflix.current_video:
            return

        vvc_params_text = self.widgets.vvc_params.text().strip()

        level = self.widgets.levelidc.currentText() if self.widgets.levelidc.currentIndex() > 0 else None

        settings = VVCSettings(
            preset=self.widgets.preset.currentText(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            tier=self.widgets.tier.currentText(),
            levelidc=level,
            vvc_params=vvc_params_text.split(":") if vvc_params_text else [],
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
        )

        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
