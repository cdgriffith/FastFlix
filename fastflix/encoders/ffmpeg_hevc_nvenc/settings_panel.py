# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import FFmpegNVENCSettings
from fastflix.models.fastflix_app import FastFlixApp

logger = logging.getLogger("fastflix")


presets = [
    "slow",
    "medium",
    "fast",
    "hp",
    "hq",
    "bd",
    "ll",
    "llhq",
    "llhp",
    "lossless",
    "losslesshp",
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
    "5000k  (1280x720p @ 60fps)",
    "6000k  (1080p @ 30fps)",
    "9000k  (1080p @ 60fps)",
    "15000k (1440p @ 30fps)",
    "25000k (1440p @ 60fps)",
    "35000k (2160p @ 30fps)",
    "50000k (2160p @ 60fps)",
    "Custom",
]

recommended_crfs = [
    "28",
    "27",
    "26",
    "25",
    "24",
    "23",
    "22",
    "21",
    "20",
    "19",
    "18",
    "17",
    "16",
    "15",
    "14",
    "Custom",
]

pix_fmts = ["8-bit: yuv420p", "10-bit: p010le"]


class NVENC(SettingPanel):
    profile_name = "ffmpeg_hevc_nvenc"

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
        grid.addLayout(self.init_max_mux(), 1, 0, 1, 2)
        grid.addLayout(self.init_tune(), 2, 0, 1, 2)
        grid.addLayout(self.init_profile(), 3, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 4, 0, 1, 2)
        grid.addLayout(self.init_tier(), 5, 0, 1, 2)
        grid.addLayout(self.init_rc(), 6, 0, 1, 2)
        grid.addLayout(self.init_spatial_aq(), 7, 0, 1, 2)

        grid.addLayout(self.init_hw_accel(), 4, 2, 1, 1)

        a = QtWidgets.QHBoxLayout()
        a.addLayout(self.init_rc_lookahead())
        a.addStretch(1)
        a.addLayout(self.init_level())
        a.addStretch(1)
        a.addLayout(self.init_gpu())
        a.addStretch(1)
        a.addLayout(self.init_b_ref_mode())
        grid.addLayout(a, 3, 2, 1, 4)

        grid.setRowStretch(9, 1)

        # guide_label = QtWidgets.QLabel(
        #     link("https://trac.ffmpeg.org/wiki/Encode/H.264", t("FFMPEG AVC / H.264 Encoding Guide"))
        # )
        # guide_label.setAlignment(QtCore.Qt.AlignBottom)
        # guide_label.setOpenExternalLinks(True)
        # grid.addWidget(guide_label, 11, 0, 1, 6)

        self.setLayout(grid)
        self.hide()

    def init_preset(self):
        return self._add_combo_box(
            label="Preset",
            widget_name="preset",
            options=presets,
            tooltip=("preset: The slower the preset, the better the compression and quality"),
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

    def init_profile(self):
        return self._add_combo_box(
            label="Profile_encoderopt",
            widget_name="profile",
            tooltip="Enforce an encode profile",
            options=["main", "main10", "rext"],
            opt="profile",
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
            tooltip="Set the encoding tier",
            widget_name="tier",
            options=["main", "high"],
            opt="tier",
        )

    def init_rc(self):
        return self._add_combo_box(
            label="Rate Control",
            tooltip="Override the preset rate-control",
            widget_name="rc",
            options=[
                "default",
                "vbr",
                "cbr",
                "vbr_minqp",
                "ll_2pass_quality",
                "ll_2pass_size",
                "vbr_2pass",
                "cbr_ld_hq",
                "cbr_hq",
                "vbr_hq",
            ],
            opt="rc",
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
            tooltip="",
            widget_name="spatial_aq",
            options=["off", "on"],
            opt="spatial_aq",
        )

    def init_rc_lookahead(self):
        return self._add_text_box(
            label="RC Lookahead",
            tooltip="",
            widget_name="rc_lookahead",
            opt="rc_lookahead",
            validator="int",
            default="0",
            width=30,
        )

    def init_level(self):
        layout = self._add_combo_box(
            label="Level",
            tooltip="Set the encoding level restriction",
            widget_name="level",
            options=["auto", "1.0", "2.0", "2.1", "3.0", "3.1", "4.0", "4.1", "5.0", "5.1", "5.2", "6.0", "6.1", "6.2"],
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
        self.widgets.gpu.setMinimumWidth(50)
        return layout

    def init_modes(self):
        layout = self._add_modes(recommended_bitrates, recommended_crfs, qp_name="qp")
        self.qp_radio.setChecked(False)
        self.bitrate_radio.setChecked(True)
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

        settings = FFmpegNVENCSettings(
            preset=self.widgets.preset.currentText().split("-")[0].strip(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            profile=self.widgets.profile.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
            tune=tune.split("-")[0].strip(),
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            rc=self.widgets.rc.currentText() if self.widgets.rc.currentIndex() != 0 else None,
            spatial_aq=self.widgets.spatial_aq.currentIndex(),
            rc_lookahead=int(self.widgets.rc_lookahead.text() or 0),
            level=self.widgets.level.currentText() if self.widgets.level.currentIndex() != 0 else None,
            gpu=int(self.widgets.gpu.currentText() or -1) if self.widgets.gpu.currentIndex() != 0 else -1,
            b_ref_mode=self.widgets.b_ref_mode.currentText(),
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
