#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import VVCSettings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import loading_movie, get_icon
from fastflix.shared import link
from fastflix.widgets.background_tasks import ExtractHDR10

logger = logging.getLogger("fastflix")

presets = ["faster", "fast", "medium", "slow", "slower"]

"""
libvvenc-vvc encoder AVOptions:
  -preset            <int>        E..V....... set encoding preset(0: faster - 4: slower (from 0 to 4) (default medium)
     faster          0            E..V....... 0
     fast            1            E..V....... 1
     medium          2            E..V....... 2
     slow            3            E..V....... 3
     slower          4            E..V....... 4
  -qp                <int>        E..V....... set quantization (from 0 to 63) (default 32)
  -period            <int>        E..V....... set (intra) refresh period in seconds (from 1 to INT_MAX) (default 1)
  -subjopt           <boolean>    E..V....... set subjective (perceptually motivated) optimization (default true)
  -vvenc-params      <dictionary> E..V....... set the vvenc configuration using a :-separated list of key=value parameters
  -levelidc          <int>        E..V....... vvc level_idc (from 0 to 105) (default 0)
     0               0            E..V....... auto
     1               16           E..V....... 1
     2               32           E..V....... 2
     2.1             35           E..V....... 2.1
     3               48           E..V....... 3
     3.1             51           E..V....... 3.1
     4               64           E..V....... 4
     4.1             67           E..V....... 4.1
     5               80           E..V....... 5
     5.1             83           E..V....... 5.1
     5.2             86           E..V....... 5.2
     6               96           E..V....... 6
     6.1             99           E..V....... 6.1
     6.2             102          E..V....... 6.2
     6.3             105          E..V....... 6.3
  -tier              <int>        E..V....... set vvc tier (from 0 to 1) (default main)
     main            0            E..V....... main
     high            1            E..V....... high

"""

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
        # breaker_label.setFont(QtGui.QFont("", 8, weight=55))

        breaker.addWidget(get_breaker(), stretch=1)
        breaker.addWidget(breaker_label, alignment=QtCore.Qt.AlignHCenter)
        breaker.addWidget(get_breaker(), stretch=1)

        grid.addLayout(breaker, 5, 0, 1, 6)

        # grid.addLayout(self.init_aq_mode(), 6, 0, 1, 2)
        # grid.addLayout(self.init_frame_threads(), 7, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 8, 0, 1, 2)
        # grid.addLayout(self.init_vvc_row(), 6, 2, 1, 4)
        # grid.addLayout(self.init_vvc_row_two(), 7, 2, 1, 4)
        # grid.addLayout(self.init_hdr10_opt(), 5, 2, 1, 1)
        # grid.addLayout(self.init_repeat_headers(), 5, 3, 1, 1)
        # grid.addLayout(self.init_aq_mode(), 5, 4, 1, 2)

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
        return self._add_combo_box(
            label="IDC Level",
            tooltip="Set the IDC level",
            widget_name="levelidc",
            options=[
                "0",
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
                "Slow is highest personal recommenced, as past that is much smaller gains"
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
        self.widgets.vvc_params.setText(
            ":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "vvc_params"))
        )
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

        settings = VVCSettings(
            preset=self.widgets.preset.currentText(),
            # intra_encoding=self.widgets.intra_encoding.isChecked(),

            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            # profile=self.widgets.profile.currentText(),
            # hdr10=self.widgets.hdr10.isChecked(),
            # hdr10_opt=self.widgets.hdr10_opt.isChecked(),
            # dhdr10_opt=self.widgets.dhdr10_opt.isChecked(),
            # repeat_headers=self.widgets.repeat_headers.isChecked(),
            # aq_mode=self.widgets.aq_mode.currentIndex(),
            # bframes=self.widgets.bframes.currentIndex(),
            # b_adapt=self.widgets.b_adapt.currentIndex(),
            # intra_smoothing=self.widgets.intra_smoothing.isChecked(),
            # frame_threads=self.widgets.frame_threads.currentIndex(),
            # tune=self.widgets.tune.currentText(),
            tier=self.widgets.tier.currentText(),
            levelidc=self.widgets.levelidc.currentText(),
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
