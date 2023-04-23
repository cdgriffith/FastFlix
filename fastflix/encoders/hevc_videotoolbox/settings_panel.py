# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.models.encode import HEVCVideoToolboxSettings
from fastflix.models.fastflix_app import FastFlixApp

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k   (320x240p @ 24,25,30)",
    "276k   (640x360p @ 24,25,30)",
    "512k   (640x480p @ 24,25,30)",
    "1024k  (1280x720p @ 24,25,30)",
    "1800k (1280x720p @ 50,60)",
    "1800k (1920x1080p @ 24,25,30)",
    "3000k (1920x1080p @ 50,60)",
    "6000k (2560x1440p @ 24,25,30)",
    "9000k (2560x1440p @ 50,60)",
    "12000k (3840x2160p @ 24,25,30)",
    "18000k (3840x2160p @ 50,60)",
    "Custom",
]

recommended_crfs = [
    "37 (240p)",
    "36 (360p)",
    "33 (480p)",
    "32 (720p)",
    "31 (1080p)",
    "24 (1440p)",
    "15 (2160p)",
    "Custom",
]

pix_fmts = [
    "8-bit: yuv420p",
    "10-bit: p010le",
]


class HEVCVideoToolbox(SettingPanel):
    profile_name = "hevc_videotoolbox"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None)

        self.mode = "Q"

        grid.addLayout(self.init_pix_fmt(), 0, 0, 1, 2)
        grid.addLayout(self.init_profile(), 1, 0, 1, 2)
        grid.addLayout(self.init_allow_sw(), 2, 0, 1, 2)
        grid.addLayout(self.init_require_sw(), 3, 0, 1, 2)
        grid.addLayout(self.init_realtime(), 4, 0, 1, 2)
        grid.addLayout(self.init_frames_before(), 5, 0, 1, 2)
        grid.addLayout(self.init_frames_after(), 6, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 7, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        # grid.addWidget(QtWidgets.QWidget(), 8, 0)
        grid.setRowStretch(8, 1)
        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        # link_1 = link(
        #     "https://trac.ffmpeg.org/wiki/Encode/VP9", t("FFMPEG VP9 Encoding Guide"), app.fastflix.config.theme
        # )
        # link_2 = link(
        #     "https://developers.google.com/media/vp9/hdr-encoding/",
        #     t("Google's VP9 HDR Encoding Guide"),
        #     app.fastflix.config.theme,
        # )
        #
        # guide_label = QtWidgets.QLabel(f"{link_1} | {link_2}")
        # guide_label.setAlignment(QtCore.Qt.AlignBottom)
        # guide_label.setOpenExternalLinks(True)
        # grid.addWidget(guide_label, 11, 0, 1, 6)
        self.setLayout(grid)
        self.hide()

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_profile(self):
        return self._add_combo_box(
            label="Profile",
            tooltip="HEVC coding profile - must match bit depth",
            widget_name="profile",
            options=[
                "Auto",
                "Main",
                "Main10",
            ],
            opt="profile",
        )

    def init_allow_sw(self):
        return self._add_check_box(
            label="Allow Software Encoding",
            widget_name="allow_sw",
            opt="allow_sw",
        )

    def init_require_sw(self):
        return self._add_check_box(
            label="Require Software Encoding",
            widget_name="require_sw",
            opt="require_sw",
        )

    def init_realtime(self):
        return self._add_check_box(
            label="Realtime Encoding",
            tooltip="Hint that encoding should happen in real-time if not faster",
            widget_name="realtime",
            opt="realtime",
        )

    def init_frames_before(self):
        return self._add_check_box(
            label="Frames Before",
            tooltip="Other frames will come before the frames in this session. This helps smooth concatenation issues.",
            widget_name="frames_before",
            opt="frames_before",
        )

    def init_frames_after(self):
        return self._add_check_box(
            label="Frames After",
            tooltip="Other frames will come after the frames in this session. This helps smooth concatenation issues.",
            widget_name="frames_after",
            opt="frames_after",
        )

    def init_modes(self):
        return self._add_modes(
            recommended_bitrates, [str(x) for x in range(1, 101)], qp_name="q", disable_custom_qp=True
        )

    def mode_update(self):
        # self.widgets.custom_q.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        settings = HEVCVideoToolboxSettings(
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            profile=self.widgets.profile.currentIndex(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            allow_sw=self.widgets.allow_sw.isChecked(),
            require_sw=self.widgets.require_sw.isChecked(),
            realtime=self.widgets.realtime.isChecked(),
            frames_before=self.widgets.frames_before.isChecked(),
            frames_after=self.widgets.frames_after.isChecked(),
        )
        encode_type, q_value = self.get_mode_settings()
        settings.q = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
