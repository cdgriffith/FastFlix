# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import VP9Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

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
    "10-bit: yuv420p10le",
    "12-bit: yuv420p12le",
    "8-bit 420 Transparent: yuva420p",
    "8-bit 422: yuv422p",
    "8-bit 444: yuv444p",
    "10-bit 422: yuv422p10le",
    "10-bit 444: yuv444p10le",
    "12-bit 422: yuv422p12le",
    "12-bit 444: yuv444p12le",
]


class VP9(SettingPanel):
    profile_name = "vp9"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self.init_quality(), 1, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 2, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 3, 0, 1, 2)
        grid.addLayout(self.init_profile(), 4, 0, 1, 2)

        grid.addLayout(self.init_tile_columns(), 5, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 6, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        checkboxes = QtWidgets.QHBoxLayout()
        checkboxes.addLayout(self.init_single_pass())
        checkboxes.addStretch(1)
        checkboxes.addLayout(self.init_row_mt())
        checkboxes.addStretch(1)
        checkboxes.addLayout(self.init_fast_first_pass())

        grid.addLayout(checkboxes, 5, 2, 1, 4)

        grid.addLayout(self.init_tune_content(), 7, 0, 1, 2)
        grid.addLayout(self.init_aq_mode(), 7, 2, 1, 4)

        grid.addLayout(self.init_auto_alt_ref(), 8, 0, 1, 2)
        grid.addLayout(self.init_lag_in_frames(), 8, 2, 1, 4)

        grid.addLayout(self.init_sharpness(), 9, 0, 1, 2)

        grid.setRowStretch(10, 1)
        grid.addLayout(self._add_custom(), 11, 0, 1, 6)

        link_1 = link(
            "https://trac.ffmpeg.org/wiki/Encode/VP9", t("FFMPEG VP9 Encoding Guide"), app.fastflix.config.theme
        )
        link_2 = link(
            "https://developers.google.com/media/vp9/hdr-encoding/",
            t("Google's VP9 HDR Encoding Guide"),
            app.fastflix.config.theme,
        )

        guide_label = QtWidgets.QLabel(f"{link_1} | {link_2}")
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 12, 0, 1, 6)
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
            label="Profile_encoderopt",
            tooltip="profile: VP9 coding profile - must match bit depth",
            widget_name="profile",
            options=[
                "0: 8-bit | 4:2:0",
                "1: 8-bit | 4:2:2 or 4:4:4",
                "2: 10 or 12-bit | 4:2:0",
                "3: 10 or 12-bit | 4:2:2 or 4:4:4",
            ],
            opt="profile",
        )

    def init_quality(self):
        return self._add_combo_box(
            label="Quality",
            tooltip=(
                "good is the default and recommended for most applications\n"
                "best is recommended if you have lots of time and want the best compression efficiency."
            ),
            widget_name="quality",
            options=["realtime", "good", "best"],
            opt="quality",
        )

    def init_speed(self):
        return self._add_combo_box(
            label="Speed",
            tooltip=(
                "Using 1 or 2 will increase encoding speed at the expense of having some impact on "
                "quality and rate control accuracy.\n4 or 5 will turn off rate distortion optimization, "
                "having even more of an impact on quality."
            ),
            widget_name="speed",
            options=[str(x) for x in range(-8, 9)],
            opt="speed",
        )

    def init_row_mt(self):
        return self._add_check_box(
            label="Row multithreading",
            tooltip=(
                "This improves encoding speed significantly on systems that "
                "are otherwise underutilised when encoding VP9."
            ),
            widget_name="row_mt",
            opt="row_mt",
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Log2 of number of tile columns to encode faster (lesser quality)",
            widget_name="tile_columns",
            options=[str(x) for x in range(-1, 7)],
            opt="tile_columns",
        )

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Log2 of number of tile rows to encode faster (lesser quality)",
            widget_name="tile_rows",
            options=[str(x) for x in range(-1, 3)],
            opt="tile_rows",
        )

    def init_fast_first_pass(self):
        return self._add_check_box(
            label="Fast first pass",
            tooltip="Set speed to 4 for first pass",
            widget_name="fast_first_pass",
            opt="fast_first_pass",
        )

    def init_single_pass(self):
        return self._add_check_box(label="Single Pass (CRF)", tooltip="", widget_name="single_pass", opt="single_pass")

    def init_auto_alt_ref(self):
        return self._add_combo_box(
            label="Alt Ref Frames",
            tooltip="Enable automatic alternate reference frames.\nMost impactful VP9 quality feature for multi-pass encoding.",
            widget_name="auto_alt_ref",
            options=["Default", "0 (disabled)", "1", "2", "3", "4", "5", "6"],
            opt="auto_alt_ref",
        )

    def init_lag_in_frames(self):
        return self._add_combo_box(
            label="Lag in Frames",
            tooltip="Number of frames to look ahead for alternate reference frame selection.\nRecommended: 25.",
            widget_name="lag_in_frames",
            options=["Default", "0", "10", "16", "20", "25", "30", "40", "50"],
            opt="lag_in_frames",
        )

    def init_tune_content(self):
        return self._add_combo_box(
            label="Tune Content",
            tooltip="Content type tuning.\nscreen: for screen capture content\nfilm: for film content",
            widget_name="tune_content",
            options=["default", "screen", "film"],
            opt="tune_content",
        )

    def init_aq_mode(self):
        return self._add_combo_box(
            label="AQ Mode",
            tooltip="Adaptive quantization mode.",
            widget_name="aq_mode",
            options=["Default", "0 (none)", "1 (variance)", "2 (complexity)", "3 (cyclic)", "4 (equator360)"],
            opt="aq_mode",
        )

    def init_sharpness(self):
        return self._add_combo_box(
            label="Sharpness",
            tooltip="Loop filter sharpness (0-7).",
            widget_name="sharpness",
            options=["Default", "0", "1", "2", "3", "4", "5", "6", "7"],
            opt="sharpness",
        )

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_crfs, qp_name="crf")

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        auto_alt_ref_text = self.widgets.auto_alt_ref.currentText()
        if not auto_alt_ref_text or auto_alt_ref_text == "Default":
            auto_alt_ref = -1
        else:
            auto_alt_ref = int(auto_alt_ref_text.split()[0])

        lag_in_frames_text = self.widgets.lag_in_frames.currentText()
        lag_in_frames = -1 if not lag_in_frames_text or lag_in_frames_text == "Default" else int(lag_in_frames_text)

        aq_mode_text = self.widgets.aq_mode.currentText()
        if not aq_mode_text or aq_mode_text == "Default":
            aq_mode = -1
        else:
            aq_mode = int(aq_mode_text.split()[0])

        sharpness_text = self.widgets.sharpness.currentText()
        sharpness = -1 if not sharpness_text or sharpness_text == "Default" else int(sharpness_text)

        settings = VP9Settings(
            quality=self.widgets.quality.currentText(),
            speed=self.widgets.speed.currentText(),
            row_mt=int(self.widgets.row_mt.isChecked()),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            single_pass=self.widgets.single_pass.isChecked(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            profile=self.widgets.profile.currentIndex(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            fast_first_pass=self.widgets.fast_first_pass.isChecked(),
            tile_columns=(
                self.widgets.tile_columns.currentText() if self.widgets.tile_columns.currentIndex() > 0 else "-1"
            ),
            tile_rows=self.widgets.tile_rows.currentText() if self.widgets.tile_rows.currentIndex() > 0 else "-1",
            auto_alt_ref=auto_alt_ref,
            lag_in_frames=lag_in_frames,
            tune_content=self.widgets.tune_content.currentText(),
            aq_mode=aq_mode,
            sharpness=sharpness,
        )
        encode_type, q_value = self.get_mode_settings()
        settings.crf = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
