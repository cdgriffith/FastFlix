#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import x265Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import loading_movie, get_icon
from fastflix.shared import link
from fastflix.widgets.background_tasks import ExtractHDR10

logger = logging.getLogger("fastflix")

presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"]

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

recommended_crfs = [
    "28 (x265 default - lower quality)",
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
    "8-bit: yuv420p",
    "10-bit: yuv420p10le",
    "12-bit: yuv420p12le",
    "8-bit 422: yuv422p",
    "8-bit 444: yuv444p",
    "10-bit 422: yuv422p10le",
    "10-bit 444: yuv444p10le",
    "12-bit 422: yuv422p12le",
    "12-bit 444: yuv444p12le",
]

# fmt: off
gop_sizes = [t("Auto"), "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17",
             "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34",
             "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51",
             "52", "53", "54", "55", "56", "57", "58", "59", "60", "70", "80", "90", "100", "110", "120", "140", "160",
             "180", "200", "220", "240", "260", "280", "300", "400", "500", "600", "700", "800", "900", "1000"]
# fmt: on


def get_breaker():
    breaker_line = QtWidgets.QWidget()
    breaker_line.setMaximumHeight(2)
    breaker_line.setStyleSheet("background-color: #ccc; margin: auto 0; padding: auto 0;")
    return breaker_line


class HEVC(SettingPanel):
    profile_name = "x265"
    hdr10plus_signal = QtCore.Signal(str)
    hdr10plus_ffmpeg_signal = QtCore.Signal(str)

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.mode = "CRF"
        self.updating_settings = False
        self.extract_thread = None

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_tune(), 1, 0, 1, 2)
        grid.addLayout(self.init_profile(), 2, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 3, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 5, 4)

        breaker = QtWidgets.QHBoxLayout()
        breaker_label = QtWidgets.QLabel(t("Advanced"))
        # breaker_label.setFont(QtGui.QFont("", 8, weight=55))

        breaker.addWidget(get_breaker(), stretch=1)
        breaker.addWidget(breaker_label, alignment=QtCore.Qt.AlignHCenter)
        breaker.addWidget(get_breaker(), stretch=1)

        grid.addLayout(breaker, 5, 0, 1, 6)

        grid.addLayout(self.init_aq_mode(), 6, 0, 1, 2)
        grid.addLayout(self.init_frame_threads(), 7, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 8, 0, 1, 2)
        # grid.addLayout(self.init_gop(), 9, 0, 1, 2)
        grid.addLayout(self.init_x265_row(), 6, 2, 1, 4)
        grid.addLayout(self.init_x265_row_two(), 7, 2, 1, 4)
        # grid.addLayout(self.init_hdr10_opt(), 5, 2, 1, 1)
        # grid.addLayout(self.init_repeat_headers(), 5, 3, 1, 1)
        # grid.addLayout(self.init_aq_mode(), 5, 4, 1, 2)

        grid.addLayout(self.init_x265_params(), 8, 2, 1, 4)

        grid.addLayout(self.init_dhdr10_info(), 9, 2, 1, 3)
        grid.addLayout(self.init_dhdr10_warning_and_opt(), 9, 5, 1, 1)
        self.ffmpeg_level = QtWidgets.QLabel()
        grid.addWidget(self.ffmpeg_level, 10, 2, 1, 4)

        grid.setRowStretch(11, True)

        grid.addLayout(self._add_custom(), 12, 0, 1, 6)

        link_1 = link(
            "https://trac.ffmpeg.org/wiki/Encode/H.265",
            t("FFMPEG HEVC / H.265 Encoding Guide"),
            app.fastflix.config.theme,
        )
        link_2 = link(
            "https://codecalamity.com/encoding-uhd-4k-hdr10-videos-with-ffmpeg",
            t("CodeCalamity UHD HDR Encoding Guide"),
            app.fastflix.config.theme,
        )
        link_3 = link(
            "https://github.com/cdgriffith/FastFlix/wiki/HDR10-Plus-Metadata-Extraction",
            t("HDR10+ Metadata Extraction"),
            app.fastflix.config.theme,
        )

        guide_label = QtWidgets.QLabel(f"{link_1} | {link_2} | {link_3}")
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)

        grid.addWidget(guide_label, 13, 0, 1, 6)

        self.hdr10plus_signal.connect(self.done_hdr10plus_extract)
        self.hdr10plus_ffmpeg_signal.connect(lambda x: self.ffmpeg_level.setText(x))
        self.setLayout(grid)
        self.hide()

    def init_dhdr10_info(self):
        layout = self._add_file_select(
            label="HDR10+ Metadata",
            widget_name="hdr10plus_metadata",
            button_action=lambda: self.dhdr10_update(),
            tooltip="dhdr10_info: Path to HDR10+ JSON metadata file",
        )
        self.labels["hdr10plus_metadata"].setFixedWidth(200)
        return layout

    def init_dhdr10_warning_and_opt(self):
        label = QtWidgets.QLabel()
        label.setToolTip(
            "WARNING: This only works on a few FFmpeg builds, and it will not raise error on failure!\n"
            "Specifically, FFmpeg needs the x265 ENABLE_HDR10_PLUS option enabled on compile.\n"
            "The latest windows builds from BtbN should have this feature.\n"
            "I do not know of any public Linux/Mac ones that do."
        )
        icon = QtGui.QIcon(get_icon("onyx-warning", self.app.fastflix.config.theme))
        label.setPixmap(icon.pixmap(22))
        layout = QtWidgets.QHBoxLayout()

        self.extract_button = QtWidgets.QPushButton(t("Extract HDR10+"))
        self.extract_button.hide()
        self.extract_button.clicked.connect(self.extract_hdr10plus)

        self.extract_label = QtWidgets.QLabel(self)
        self.extract_label.hide()
        self.movie = QtGui.QMovie(loading_movie)
        self.movie.setScaledSize(QtCore.QSize(25, 25))
        self.extract_label.setMovie(self.movie)

        layout.addWidget(self.extract_button)
        layout.addWidget(self.extract_label)

        layout.addWidget(label)
        layout.addLayout(self.init_dhdr10_opt())
        return layout

    def init_x265_row(self):
        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self.init_hdr10())
        layout.addStretch(1)
        layout.addLayout(self.init_hdr10_opt())
        layout.addStretch(1)
        layout.addLayout(self.init_repeat_headers())
        layout.addStretch(1)
        layout.addLayout(self.init_bframes())

        return layout

    def init_x265_row_two(self):
        layout = QtWidgets.QHBoxLayout()
        # layout.addLayout(self.init_intra_encoding())
        # layout.addStretch(1)
        layout.addLayout(self.init_intra_refresh())
        layout.addStretch(1)

        layout.addLayout(self.init_intra_smoothing())
        layout.addStretch(1)
        layout.addLayout(self.init_lossless())
        layout.addStretch(1)
        layout.addLayout(self.init_b_adapt())
        return layout

    def init_hdr10(self):
        return self._add_check_box(
            label="Force HDR10 signaling",
            widget_name="hdr10",
            tooltip=(
                "hdr10: Force signaling of HDR10 parameters in SEI packets.\n"
                "Enabled automatically when --master-display or --max-cll is specified.\n"
                "Useful when there is a desire to signal 0 values for max-cll and max-fall.\n"
                "Default disabled."
            ),
            opt="hdr10",
        )

    def init_hdr10_opt(self):
        return self._add_check_box(
            label="HDR10 Optimizations",
            widget_name="hdr10_opt",
            tooltip=(
                "hdr10-opt: Enable block-level luma and chroma QP optimization for HDR10 content.\n"
                "It is recommended that AQ-mode be enabled along with this feature"
            ),
            opt="hdr10_opt",
        )

    def init_dhdr10_opt(self):
        return self._add_check_box(
            label="HDR10+ Optimizations",
            widget_name="dhdr10_opt",
            tooltip=(
                "dhdr10-opt: Reduces SEI overhead\n"
                "Only put the HDR10+ dynamic metadata in the IDR and frames where the values have changed.\n"
                "It saves a few bits and can help performance in the client's tonemapper."
            ),
            opt="dhdr10_opt",
        )

    def init_repeat_headers(self):
        return self._add_check_box(
            label="Repeat Headers",
            widget_name="repeat_headers",
            tooltip=(
                "repeat-headers: If enabled, x265 will emit VPS, SPS, and PPS headers with every keyframe.\n"
                "This is intended for use when you do not have a container to keep the stream headers for you\n"
                "and you want keyframes to be random access points."
            ),
            opt="repeat_headers",
        )

    def init_aq_mode(self):
        return self._add_combo_box(
            label="Adaptive Quantization",
            widget_name="aq_mode",
            options=[
                "disabled",
                "enabled",
                "enabled + auto-variance",
                "enabled + av + dark bias",
                "enabled + av + edge",
            ],
            tooltip=(
                "aq-mode: Adaptive Quantization operating mode.\n"
                "Raise or lower per-block quantization based on complexity analysis of the source image.\n"
                "The more complex the block, the more quantization is used.\n"
                "Default: AQ enabled with auto-variance"
            ),
            opt="aq_mode",
        )

    def init_frame_threads(self):
        return self._add_combo_box(
            label="Frame Threads",
            widget_name="frame_threads",
            options=["Auto"] + [str(x) for x in range(1, 17)],
            default=0,
            tooltip=(
                "frame-threads: Number of concurrently encoded frames.\n"
                "Using a single frame thread gives a slight improvement in compression,\n"
                "since the entire reference frames are always available for motion compensation,\n"
                "but it has severe performance implications.\n"
                "Default is an autodetected count based on the number of CPU cores and whether WPP is enabled or not.\n"
                "Over-allocation of frame threads will not improve performance,\n"
                "it will generally just increase memory use."
            ),
            opt="frame_threads",
        )

    def init_bframes(self):
        return self._add_combo_box(
            label="Maximum B frames",
            widget_name="bframes",
            options=[str(x) for x in range(17)],
            default=4,
            tooltip=(
                "bframes: Maximum number of consecutive b-frames. \n"
                "Use --bframes 0 to force all P/I low-latency encodes.\n"
                "Default 4. This parameter has a quadratic effect on the amount of memory allocated\n"
                "and the amount of work performed by the full trellis version of --b-adapt lookahead."
            ),
            opt="bframes",
        )

    def init_b_adapt(self):
        return self._add_combo_box(
            label="B Adapt",
            widget_name="b_adapt",
            options=["none", "fast", "full"],
            default=2,
            tooltip=(
                "b-adapt: Set the level of effort in determining B frame placement.\n"
                "With b-adapt 0, the GOP structure is fixed based on the values of --keyint and --bframes.\n"
                "With b-adapt 1 a light lookahead is used to choose B frame placement.\n"
                "With b-adapt 2 (trellis) a viterbi B path selection is performed\n"
                "Values: 0:none; 1:fast; 2:full(trellis) default\n"
            ),
            opt="b_adapt",
        )

    def init_intra_encoding(self):
        return self._add_check_box(
            label="Intra-Encoding",
            widget_name="intra_encoding",
            tooltip=(
                "keyint: Enable Intra-Encoding by forcing keyframes every 1 second (Blu-ray spec)\n"
                "This option is not recommended unless you need to conform \n"
                "to Blu-ray standards to burn to a physical disk"
            ),
            opt="intra_encoding",
        )

    def init_intra_smoothing(self):
        return self._add_check_box(
            label="Intra-Smoothing",
            widget_name="intra_smoothing",
            tooltip=(
                "Enable strong intra smoothing for 32x32 intra blocks.\n"
                "This flag performs bi-linear interpolation of the corner reference "
                "samples for a strong smoothing effect.\n"
                "The purpose is to prevent blocking or banding artifacts in regions with few/zero AC coefficients.\n"
                "Default enabled."
            ),
            opt="intra_smoothing",
        )

    def init_intra_refresh(self):
        return self._add_check_box(
            label="Intra-refresh",
            widget_name="intra_refresh",
            tooltip=(
                "intra-refresh: Enables Periodic Intra Refresh(PIR) instead of keyframe insertion.\n"
                "PIR can replace keyframes by inserting a column of intra blocks in non-keyframes,\n"
                "that move across the video from one side to the other and thereby refresh the image\n"
                "but over a period of multiple frames instead of a single keyframe."
            ),
            opt="intra_refresh",
        )

    def init_lossless(self):
        return self._add_check_box(
            label="Lossless",
            widget_name="lossless",
            tooltip=(
                "Enables true lossless coding by bypassing scaling, transform, quantization and in-loop filtering.\n"
                "This is used for ultra-high bitrates with zero loss of quality.\n"
                "Reconstructed output pictures are bit-exact to the input pictures.\n"
                "Lossless encodes implicitly have no rate control, all rate control options are ignored.\n"
                "Slower presets will generally achieve better compression efficiency (and generate smaller bitstreams)."
            ),
            opt="lossless",
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
            connect=self.preset_update,
            opt="preset",
        )
        return layout

    def preset_update(self):
        def set_aq(num):
            if self.widgets.tune.currentIndex() == 0:
                self.widgets.aq_mode.setCurrentIndex(num)
            if self.widgets["tune"].currentText() == "animation":
                bframes = 5
                if self.widgets.preset.currentIndex() >= 2:
                    bframes = 6
                if self.widgets.preset.currentIndex() >= 7:
                    bframes = 10
                self.widgets.bframes.setCurrentIndex(bframes)

        if self.widgets["preset"].currentText() == "ultrafast":
            self.widgets.bframes.setCurrentIndex(3)
            self.widgets.b_adapt.setCurrentIndex(0)
            set_aq(0)
        elif self.widgets["preset"].currentText() == "superfast":
            self.widgets.bframes.setCurrentIndex(3)
            self.widgets.b_adapt.setCurrentIndex(0)
            set_aq(0)
        elif self.widgets["preset"].currentText() == "veryfast":
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(0)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "faster":
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(0)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "fast":
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(0)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "medium":
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(2)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "slow":
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(2)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "slower":
            self.widgets.bframes.setCurrentIndex(8)
            self.widgets.b_adapt.setCurrentIndex(2)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "veryslow":
            self.widgets.bframes.setCurrentIndex(8)
            self.widgets.b_adapt.setCurrentIndex(2)
            set_aq(2)
        elif self.widgets["preset"].currentText() == "placebo":
            self.widgets.bframes.setCurrentIndex(8)
            self.widgets.b_adapt.setCurrentIndex(2)
            set_aq(2)

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            widget_name="tune",
            options=["default", "psnr", "ssim", "grain", "zerolatency", "fastdecode", "animation"],
            tooltip="tune: Tune the settings for a particular type of source or situation",
            connect=self.tune_update,
            opt="tune",
        )

    def tune_update(self):
        self.widgets.aq_mode.setEnabled(True)
        self.widgets.bframes.setEnabled(True)
        self.widgets.b_adapt.setEnabled(True)
        self.widgets.frame_threads.setEnabled(True)
        self.widgets.aq_mode.setCurrentIndex(2)
        self.widgets.bframes.setCurrentIndex(4)
        self.widgets.b_adapt.setCurrentIndex(2)
        self.widgets.frame_threads.setCurrentIndex(0)

        if self.widgets["tune"].currentText() == "grain":
            self.widgets.aq_mode.setCurrentIndex(0)
            self.widgets.aq_mode.setEnabled(False)
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(2)
        elif self.widgets["tune"].currentText() == "psnr":
            self.widgets.aq_mode.setCurrentIndex(0)
            self.widgets.aq_mode.setEnabled(False)
            self.widgets.bframes.setCurrentIndex(4)
            self.widgets.b_adapt.setCurrentIndex(2)
        elif self.widgets["tune"].currentText() == "zerolatency":
            self.widgets.bframes.setCurrentIndex(0)
            self.widgets.b_adapt.setCurrentIndex(0)
            self.widgets.frame_treahds.setCurrentIndex(1)
            self.widgets.bframes.setEnabled(False)
            self.widgets.b_adapt.setEnabled(False)
            self.widgets.frame_threads.setEnabled(False)
        elif self.widgets["tune"].currentText() == "animation":
            bframes = 5
            if self.widgets.preset.currentIndex() >= 2:
                bframes = 6
            if self.widgets.preset.currentIndex() >= 7:
                bframes = 10
            self.widgets.bframes.setCurrentIndex(bframes)

    def init_profile(self):
        return self._add_combo_box(
            label="Profile_encoderopt",
            tooltip="profile: Enforce an encode profile",
            widget_name="profile",
            options=[
                "default",
                "main",
                "main10",
                "mainstillpicture",
                "msp",
                "main-intra",
                "main10-intra",
                "main444-8",
                "main444-intra",
                "main444-stillpicture",
                "main422-10 ",
                "main422-10-intra",
                "main444-10",
                "main444-10-intra",
                "main12",
                "main12-intra",
                "main422-12 ",
                "main422-12-intra",
                "main444-12 ",
                "main444-12-intra",
                "main444-16-intra ",
                "main444-16-stillpicture",
            ],
            opt="profile",
        )

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

    def init_gop(self):
        return self._add_combo_box(
            label="Gop Size", tooltip="GOP Size", widget_name="gop_size", opt="gop_size", options=gop_sizes
        )

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_crfs, qp_name="crf", show_bitrate_passes=True)

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def init_x265_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.x265_params = QtWidgets.QLabel(t("Additional x265 params"))
        self.labels.x265_params.setFixedWidth(200)
        tool_tip = (
            f"{t('Extra x265 params in opt=1:opt2=0 format')},\n"
            f"{t('cannot modify generated settings')}\n"
            f"{t('examples: level-idc=4.1:rc-lookahead=10')} \n"
        )
        self.labels.x265_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.x265_params)
        self.widgets.x265_params = QtWidgets.QLineEdit()
        self.widgets.x265_params.setToolTip(tool_tip)
        self.widgets.x265_params.setText(
            ":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "x265_params"))
        )
        self.opts["x265_params"] = "x265_params"
        self.widgets.x265_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.x265_params)
        return layout

    def setting_change(self, update=True, pix_change=False):
        def hdr_opts():
            if not self.widgets.pix_fmt.currentText().startswith(
                "8-bit"
            ) and self.app.fastflix.current_video.color_space.startswith("bt2020"):
                self.widgets.hdr10_opt.setDisabled(False)
                if self.app.fastflix.current_video.master_display or self.app.fastflix.current_video.cll:
                    self.widgets.hdr10.setDisabled(True)
                    self.widgets.hdr10.setChecked(True)
                    self.widgets.hdr10_opt.setChecked(True)
                    self.widgets.repeat_headers.setChecked(True)
                    self.widgets.repeat_headers.setDisabled(True)
                else:
                    self.widgets.hdr10.setDisabled(False)
                    self.widgets.hdr10.setChecked(False)
                    self.widgets.hdr10_opt.setChecked(False)
                    self.widgets.repeat_headers.setChecked(False)
                    self.widgets.repeat_headers.setDisabled(False)
            else:
                self.widgets.hdr10.setDisabled(True)
                self.widgets.hdr10_opt.setDisabled(True)
                self.widgets.hdr10.setChecked(False)
                self.widgets.hdr10_opt.setChecked(False)
                self.widgets.repeat_headers.setChecked(False)
                self.widgets.repeat_headers.setDisabled(False)

        if self.updating_settings or not self.main.input_video:
            return
        self.updating_settings = True
        if pix_change:
            hdr_opts()
            self.main.page_update()
            self.updating_settings = False
            return

        if self.main.remove_hdr:
            # self.widgets.pix_fmt.clear()
            # self.widgets.pix_fmt.addItems([pix_fmts[0]])
            # self.widgets.pix_fmt.setCurrentIndex(0)
            self.widgets.hdr10_opt.setDisabled(True)
            self.widgets.hdr10_opt.setChecked(False)
            self.widgets.hdr10.setDisabled(True)
            self.widgets.hdr10.setChecked(False)
            self.widgets.repeat_headers.setChecked(False)
            self.widgets.repeat_headers.setDisabled(False)
        else:
            # bit_depth = self.app.fastflix.current_video.streams["video"][self.main.video_track].bit_depth
            # self.widgets.pix_fmt.clear()
            # # if bit_depth == 12:
            # #     self.widgets.pix_fmt.addItems(pix_fmts[2:])
            # #     self.widgets.pix_fmt.setCurrentIndex(0)
            # if bit_depth >= 10:
            #     self.widgets.pix_fmt.addItems(pix_fmts[1:])
            #     self.widgets.pix_fmt.setCurrentIndex(0)
            # else:
            hdr_opts()
        # self.widgets.pix_fmt.addItems(pix_fmts)
        # self.widgets.pix_fmt.setCurrentIndex(1)

        if update:
            self.main.page_update()
        self.updating_settings = False

    def new_source(self):
        if not self.app.fastflix.current_video:
            return
        super().new_source()
        self.setting_change()
        if self.app.fastflix.current_video.hdr10_plus:
            self.extract_button.show()
        else:
            self.extract_button.hide()
        if self.extract_thread:
            try:
                self.extract_thread.terminate()
            except Exception:
                pass

    def update_video_encoder_settings(self):
        if not self.app.fastflix.current_video:
            return

        x265_params_text = self.widgets.x265_params.text().strip()

        settings = x265Settings(
            preset=self.widgets.preset.currentText(),
            # intra_encoding=self.widgets.intra_encoding.isChecked(),
            intra_refresh=self.widgets.intra_refresh.isChecked(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            profile=self.widgets.profile.currentText(),
            hdr10=self.widgets.hdr10.isChecked(),
            hdr10_opt=self.widgets.hdr10_opt.isChecked(),
            dhdr10_opt=self.widgets.dhdr10_opt.isChecked(),
            repeat_headers=self.widgets.repeat_headers.isChecked(),
            aq_mode=self.widgets.aq_mode.currentIndex(),
            bframes=self.widgets.bframes.currentIndex(),
            b_adapt=self.widgets.b_adapt.currentIndex(),
            intra_smoothing=self.widgets.intra_smoothing.isChecked(),
            frame_threads=self.widgets.frame_threads.currentIndex(),
            tune=self.widgets.tune.currentText(),
            x265_params=x265_params_text.split(":") if x265_params_text else [],
            hdr10plus_metadata=self.widgets.hdr10plus_metadata.text().strip(),  # .replace("\\", "/"),
            lossless=self.widgets.lossless.isChecked(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            bitrate_passes=int(self.widgets.bitrate_passes.currentText()),
            # gop_size=int(self.widgets.gop_size.currentText()) if self.widgets.gop_size.currentIndex() > 0 else 0,
        )

        encode_type, q_value = self.get_mode_settings()
        settings.crf = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
