# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import x264Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

logger = logging.getLogger("fastflix")

presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"]

recommended_bitrates = [
    "500k    (320x240p @ 30fps)",
    "800k    (640x360p @ 30fps)",
    "1000k  (640x480p @ 30fps)",
    "1500k  (1280x720p @ 30fps)",
    "3000k  (1280x720p @ 60fps)",
    "5000k  (1080p @ 30fps)",
    "8000k  (1080p @ 60fps)",
    "12000k (1440p @ 30fps)",
    "20000k (1440p @ 60fps)",
    "30000k (2160p @ 30fps)",
    "45000k (2160p @ 60fps)",
    "Custom",
]

recommended_crfs = [
    "28 (lower quality)",
    "27",
    "26",
    "25",
    "24",
    "23 (x264 default)",
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
    "8-bit: yuv420p",
    "10-bit: yuv420p10le",
    "8-bit 422: yuv422p",
    "8-bit 444: yuv444p",
    "10-bit 422: yuv422p10le",
    "10-bit 444: yuv444p10le",
]


class AVC(SettingPanel):
    profile_name = "x264"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(mode=None)

        self.mode = "CRF"
        self.updating_settings = False

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 1, 0, 1, 2)
        grid.addLayout(self.init_tune(), 2, 0, 1, 2)
        grid.addLayout(self.init_profile(), 3, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 4, 0, 1, 2)

        grid.setRowStretch(9, 1)

        guide_label = QtWidgets.QLabel(
            link(
                "https://trac.ffmpeg.org/wiki/Encode/H.264",
                t("FFMPEG AVC / H.264 Encoding Guide"),
                app.fastflix.config.theme,
            )
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, 1, 6)

        self.setLayout(grid)
        self.hide()

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

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            widget_name="tune",
            tooltip="Tune the settings for a particular type of source or situation",
            options=[
                "default",
                "film",
                "animation",
                "grain",
                "stillimage",
                "psnr",
                "ssim",
                "zerolatency",
                "fastdecode",
            ],
            opt="tune",
        )

    def init_profile(self):
        return self._add_combo_box(
            label="Profile_encoderopt",
            widget_name="profile",
            tooltip="Enforce an encode profile",
            options=["default", "baseline", "main", "high", "high10", "high422", "high444"],
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

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_crfs, qp_name="crf", show_bitrate_passes=True)

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
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

        settings = x264Settings(
            preset=self.widgets.preset.currentText(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            profile=self.widgets.profile.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            extra=self.ffmpeg_extras,
            tune=tune if tune.lower() != "default" else None,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            bitrate_passes=int(self.widgets.bitrate_passes.currentText()),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.crf = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
