# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import FFmpegAV1NVENCSettings
from fastflix.models.fastflix_app import FastFlixApp

logger = logging.getLogger("fastflix")


presets = [
    "p1",
    "p2",
    "p3",
    "p4",
    "p5",
    "p6",
    "p7",
]

recommended_bitrates = [
    "800k   (320x240p @ 30fps)",
    "1000k  (640x360p @ 30fps)",
    "1500k  (640x480p @ 30fps)",
    "2000k  (1280x720p @ 30fps)",
    "4000k  (1280x720p @ 60fps)",
    "5000k  (1080p @ 30fps)",
    "8000k  (1080p @ 60fps)",
    "12000k (1440p @ 30fps)",
    "20000k (1440p @ 60fps)",
    "30000k (2160p @ 30fps)",
    "40000k (2160p @ 60fps)",
    "Custom",
]

recommended_crfs = [
    "38",
    "35",
    "33",
    "30",
    "28",
    "26",
    "24",
    "22",
    "20",
    "18",
    "16",
    "14",
    "Custom",
]

pix_fmts = ["8-bit: yuv420p", "10-bit: p010le"]


class AV1NVENC(SettingPanel):
    profile_name = "ffmpeg_av1_nvenc"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(mode=None)

        self.mode = "CRF"
        self.updating_settings = False

        grid.addLayout(self.init_modes(), 0, 2, 3, 4)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_tune(), 1, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 2, 0, 1, 2)
        grid.addLayout(self.init_tier(), 3, 0, 1, 2)
        grid.addLayout(self.init_rc(), 4, 0, 1, 2)
        grid.addLayout(self.init_multipass(), 5, 0, 1, 2)
        grid.addLayout(self.init_spatial_aq(), 6, 0, 1, 2)
        grid.addLayout(self.init_temporal_aq(), 7, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 8, 0, 1, 2)

        grid.addLayout(self.init_hw_accel(), 3, 2, 1, 1)

        a = QtWidgets.QHBoxLayout()
        a.addLayout(self.init_rc_lookahead())
        a.addStretch(1)
        a.addLayout(self.init_level())
        a.addStretch(1)
        a.addLayout(self.init_gpu())
        a.addStretch(1)
        a.addLayout(self.init_b_ref_mode())
        a.addStretch(1)
        a.addLayout(self.init_aq_strength())
        grid.addLayout(a, 4, 2, 1, 4)

        grid.setRowStretch(9, 1)

        self.setLayout(grid)
        self.hide()

    def init_preset(self):
        return self._add_combo_box(
            label="Preset",
            widget_name="preset",
            options=presets,
            tooltip="preset: p1 (fastest) to p7 (slowest/best quality)",
            connect="default",
            opt="preset",
        )

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            widget_name="tune",
            tooltip="Tune the settings for a particular type of source or situation\nhq - High Quality, uhq - Ultra High Quality, ll - Low Latency, ull - Ultra Low Latency",
            options=["hq", "uhq", "ll", "ull", "lossless"],
            opt="tune",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_tier(self):
        return self._add_combo_box(
            label="Tier",
            tooltip="Set the encoding tier (0 = main, 1 = high)",
            widget_name="tier",
            options=["0", "1"],
            opt="tier",
        )

    def init_rc(self):
        return self._add_combo_box(
            label="Rate Control",
            tooltip="Override the preset rate-control",
            widget_name="rc",
            options=["default", "constqp", "vbr", "cbr"],
            opt="rc",
        )

    def init_multipass(self):
        return self._add_combo_box(
            label="Multipass",
            tooltip="Set multipass encoding\ndisabled - Single pass\nqres - Two pass (quarter resolution first pass)\nfullres - Two pass (full resolution first pass)",
            widget_name="multipass",
            options=["disabled", "qres", "fullres"],
            opt="multipass",
        )

    def init_hw_accel(self):
        return self._add_check_box(
            opt="hw_accel",
            label="Hardware Decoding",
            tooltip="Use hardware decoding",
            widget_name="hw_accel",
        )

    def init_spatial_aq(self):
        return self._add_combo_box(
            label="Spatial AQ",
            tooltip="Enable spatial adaptive quantization for better quality in complex areas",
            widget_name="spatial_aq",
            options=["off", "on"],
            opt="spatial_aq",
        )

    def init_temporal_aq(self):
        return self._add_combo_box(
            label="Temporal AQ",
            tooltip="Enable temporal adaptive quantization for better quality in scenes with motion",
            widget_name="temporal_aq",
            options=["off", "on"],
            opt="temporal_aq",
        )

    def init_rc_lookahead(self):
        return self._add_text_box(
            label="RC Lookahead",
            tooltip="Number of frames to look ahead for rate-control (0 = disabled, 10-20 recommended)",
            widget_name="rc_lookahead",
            opt="rc_lookahead",
            validator="int",
            default="16",
            width=30,
        )

    def init_level(self):
        layout = self._add_combo_box(
            label="Level",
            tooltip="Set the encoding level restriction",
            widget_name="level",
            options=[
                "auto",
                "2.0",
                "2.1",
                "2.2",
                "2.3",
                "3.0",
                "3.1",
                "3.2",
                "3.3",
                "4.0",
                "4.1",
                "4.2",
                "4.3",
                "5.0",
                "5.1",
                "5.2",
                "5.3",
                "6.0",
                "6.1",
                "6.2",
                "6.3",
                "7.0",
                "7.1",
                "7.2",
                "7.3",
            ],
            opt="level",
        )
        self.widgets.level.setMinimumWidth(60)
        return layout

    def init_gpu(self):
        layout = self._add_combo_box(
            label="GPU",
            tooltip="Selects which NVENC capable GPU to use. First GPU is 0, second is 1, and so on",
            widget_name="gpu",
            opt="gpu",
            options=["any"] + [str(x) for x in range(8)],
        )
        self.widgets.gpu.setMinimumWidth(50)
        return layout

    def init_b_ref_mode(self):
        layout = self._add_combo_box(
            label="B Ref Mode",
            tooltip="Use B frames as references",
            widget_name="b_ref_mode",
            opt="b_ref_mode",
            options=["disabled", "each", "middle"],
        )
        self.widgets.b_ref_mode.setMinimumWidth(50)
        return layout

    def init_aq_strength(self):
        layout = self._add_combo_box(
            label="AQ Strength",
            tooltip="When Spatial AQ is enabled, sets AQ strength (1 = low, 15 = aggressive, default 8)",
            widget_name="aq_strength",
            opt="aq_strength",
            options=[str(x) for x in range(1, 16)],
        )
        self.widgets.aq_strength.setMinimumWidth(50)
        return layout

    def init_modes(self):
        layout = self._add_modes(recommended_bitrates, recommended_crfs, qp_name="qp")
        self.qp_radio.setChecked(True)
        self.bitrate_radio.setChecked(False)
        return layout

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def setting_change(self, update=True):
        if self.updating_settings:
            return
        self.updating_settings = True

        if update:
            self.main.page_update()
        self.updating_settings = False

    def update_video_encoder_settings(self):
        tune = self.widgets.tune.currentText()

        settings = FFmpegAV1NVENCSettings(
            preset=self.widgets.preset.currentText(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
            tune=tune.split("-")[0].strip(),
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            rc=self.widgets.rc.currentText() if self.widgets.rc.currentIndex() != 0 else None,
            multipass=self.widgets.multipass.currentText(),
            spatial_aq=self.widgets.spatial_aq.currentIndex(),
            temporal_aq=self.widgets.temporal_aq.currentIndex(),
            rc_lookahead=int(self.widgets.rc_lookahead.text() or 0),
            level=self.widgets.level.currentText() if self.widgets.level.currentIndex() != 0 else None,
            gpu=int(self.widgets.gpu.currentText() or -1) if self.widgets.gpu.currentIndex() != 0 else -1,
            b_ref_mode=self.widgets.b_ref_mode.currentText(),
            aq_strength=int(self.widgets.aq_strength.currentText() or 8),
            tier=self.widgets.tier.currentText(),
            hw_accel=self.widgets.hw_accel.isChecked(),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
