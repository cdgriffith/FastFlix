# -*- coding: utf-8 -*-
import logging
from pathlib import Path

from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import AOMAV1Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import loading_movie
from fastflix.shared import link

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "100k   (320x240p @ 24,25,30)",
    "200k   (640x360p @ 24,25,30)",
    "400k   (640x480p @ 24,25,30)",
    "800k  (1280x720p @ 24,25,30)",
    "1200k (1280x720p @ 50,60)",
    "1200k (1920x1080p @ 24,25,30)",
    "2000k (1920x1080p @ 50,60)",
    "4000k (2560x1440p @ 24,25,30)",
    "6000k (2560x1440p @ 50,60)",
    "9000k (3840x2160p @ 24,25,30)",
    "13000k (3840x2160p @ 50,60)",
    "Custom",
]

recommended_crfs = ["34", "32", "30", "28", "26", "24", "22", "20", "Custom"]

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

denoise_options = [
    "0 - Disabled",
    "5 - Light",
    "10 - Medium",
    "25 - Heavy",
    "50 - Maximum",
    "Custom",
]


class AV1(SettingPanel):
    profile_name = "aom_av1"
    hdr10plus_signal = QtCore.Signal(str)
    hdr10plus_ffmpeg_signal = QtCore.Signal(str)

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app
        self.extract_thread = None

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None)

        self.mode = "CRF"

        grid.addLayout(self.init_cpu_used(), 0, 0, 1, 2)
        grid.addLayout(self.init_row_mt(), 1, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_usage(), 4, 0, 1, 2)
        grid.addLayout(self.init_tune(), 5, 0, 1, 2)
        grid.addLayout(self.init_aq_mode(), 6, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 7, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 8, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self.init_denoise(), 5, 2, 1, 4)
        grid.addLayout(self.init_aom_params(), 6, 2, 1, 4)
        grid.addLayout(self.init_hdr10plus_row(), 7, 2, 1, 4)

        self.ffmpeg_level = QtWidgets.QLabel()
        grid.addWidget(self.ffmpeg_level, 8, 2, 1, 4)

        grid.addLayout(self._add_custom(), 10, 0, 1, 6)
        grid.setRowStretch(9, 1)
        guide_label = QtWidgets.QLabel(
            link("https://trac.ffmpeg.org/wiki/Encode/AV1", t("FFMPEG AV1 Encoding Guide"), app.fastflix.config.theme)
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, -1, 1)

        self.hdr10plus_signal.connect(self.done_hdr10plus_extract)
        self.hdr10plus_ffmpeg_signal.connect(lambda x: self.ffmpeg_level.setText(x))
        self.setLayout(grid)
        self.hide()

    def init_cpu_used(self):
        return self._add_combo_box(
            label="CPU Used",
            tooltip="Quality/Speed ratio modifier (defaults to 4)",
            widget_name="cpu_used",
            options=[str(x) for x in range(0, 9)],
            opt="cpu_used",
        )

    def init_row_mt(self):
        return self._add_combo_box(
            label="Row Multi-Threading",
            tooltip="Enable row based multi-threading",
            widget_name="row_mt",
            options=["default", "enabled", "disabled"],
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
            options=[str(x) for x in range(-1, 7)],
            opt="tile_rows",
        )

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

    def init_usage(self):
        return self._add_combo_box(
            label="Usage",
            tooltip="Quality and compression efficiency vs speed trade-off",
            widget_name="usage",
            options=["good", "realtime", "allintra"],
            opt="usage",
        )

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            tooltip="Optimize encoding for different quality metrics",
            widget_name="tune",
            options=["default", "psnr", "ssim"],
            opt="tune",
        )

    def init_aq_mode(self):
        return self._add_combo_box(
            label="AQ Mode",
            tooltip="Adaptive quantization mode for quality distribution",
            widget_name="aq_mode",
            options=["default", "0 - None", "1 - Variance", "2 - Complexity", "3 - Cyclic"],
            opt="aq_mode",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_denoise(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.denoise = QtWidgets.QLabel(t("Denoise"))
        self.labels.denoise.setFixedWidth(200)
        self.labels.denoise.setToolTip(t("Noise removal amount (0=off, higher=more denoising)"))
        layout.addWidget(self.labels.denoise)
        self.widgets.denoise = QtWidgets.QComboBox()
        self.widgets.denoise.addItems(denoise_options)
        self.widgets.denoise.setToolTip(t("Noise removal amount (0=off, higher=more denoising)"))
        self.widgets.denoise.currentIndexChanged.connect(lambda: self.denoise_update())
        # denoise is handled manually in reload() due to custom combo box format
        layout.addWidget(self.widgets.denoise)
        self.widgets.custom_denoise = QtWidgets.QLineEdit()
        self.widgets.custom_denoise.setFixedWidth(60)
        self.widgets.custom_denoise.setDisabled(True)
        self.widgets.custom_denoise.setToolTip(t("Custom denoise value (0-50)"))
        self.widgets.custom_denoise.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.custom_denoise)

        saved = self.app.fastflix.config.encoder_opt(self.profile_name, "denoise_noise_level")
        if saved and str(saved) != "0":
            matched = False
            for i, opt in enumerate(denoise_options):
                if opt.startswith(str(saved)):
                    self.widgets.denoise.setCurrentIndex(i)
                    matched = True
                    break
            if not matched:
                self.widgets.denoise.setCurrentIndex(len(denoise_options) - 1)
                self.widgets.custom_denoise.setText(str(saved))

        return layout

    def denoise_update(self):
        custom = self.widgets.denoise.currentText() == "Custom"
        self.widgets.custom_denoise.setDisabled(not custom)
        self.main.page_update()

    def reload(self):
        super().reload()
        saved = self.app.fastflix.current_video.video_settings.video_encoder_settings.denoise_noise_level
        if saved and str(saved) != "0":
            matched = False
            for i, opt in enumerate(denoise_options):
                if opt.startswith(str(saved)):
                    self.widgets.denoise.setCurrentIndex(i)
                    matched = True
                    break
            if not matched:
                self.widgets.denoise.setCurrentIndex(len(denoise_options) - 1)
                self.widgets.custom_denoise.setText(str(saved))
        else:
            self.widgets.denoise.setCurrentIndex(0)

    def init_aom_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.aom_params = QtWidgets.QLabel(t("Additional aom params"))
        self.labels.aom_params.setFixedWidth(200)
        tool_tip = f"{t('Extra aom params in opt=1:opt2=0 format')},\n{t('cannot modify generated settings')}"
        self.labels.aom_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.aom_params)
        self.widgets.aom_params = QtWidgets.QLineEdit()
        self.widgets.aom_params.setToolTip(tool_tip)
        self.widgets.aom_params.setText(":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "aom_params")))
        self.opts["aom_params"] = "aom_params"
        self.widgets.aom_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.aom_params)
        return layout

    def init_hdr10plus_row(self):
        layout = QtWidgets.QHBoxLayout()

        self.hdr10plus_status_label = QtWidgets.QLabel()
        self.hdr10plus_status_label.hide()
        layout.addWidget(self.hdr10plus_status_label)

        self.extract_button = QtWidgets.QPushButton(t("Extract HDR10+"))
        self.extract_button.hide()
        self.extract_button.clicked.connect(self.extract_hdr10plus)
        layout.addWidget(self.extract_button)

        self.extract_label = QtWidgets.QLabel(self)
        self.extract_label.hide()
        self.movie = QtGui.QMovie(loading_movie)
        self.movie.setScaledSize(QtCore.QSize(25, 25))
        self.extract_label.setMovie(self.movie)
        layout.addWidget(self.extract_label)

        layout.addStretch(1)
        return layout

    def done_hdr10plus_extract(self, metadata: str):
        self.extract_button.show()
        self.extract_label.hide()
        self.movie.stop()
        self.ffmpeg_level.setText("")
        if Path(metadata).exists():
            logger.info(f"HDR10+ metadata extracted to {metadata}")

    def new_source(self):
        if not self.app.fastflix.current_video:
            return
        super().new_source()
        if self.app.fastflix.current_video.hdr10_plus:
            self.extract_button.show()
            if self.app.fastflix.libavcodec_version >= 62:
                self.hdr10plus_status_label.setStyleSheet("")
                self.hdr10plus_status_label.setText(t("HDR10+ detected — will be preserved via FFmpeg passthrough"))
            else:
                self.hdr10plus_status_label.setStyleSheet("")
                self.hdr10plus_status_label.setText(t("HDR10+ detected but requires FFmpeg 8.0+ for AV1 passthrough"))
            self.hdr10plus_status_label.show()
        else:
            self.extract_button.hide()
            self.hdr10plus_status_label.hide()
        if self.extract_thread:
            try:
                self.extract_thread.terminate()
            except Exception:
                pass

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_crfs, qp_name="crf")

    def mode_update(self):
        self.widgets.custom_crf.setDisabled(self.widgets.crf.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        # Parse denoise value from combo box or custom field
        denoise_text = self.widgets.denoise.currentText()
        if denoise_text == "Custom":
            try:
                denoise_noise_level = int(self.widgets.custom_denoise.text())
            except (ValueError, TypeError):
                denoise_noise_level = 0
        else:
            denoise_noise_level = int(denoise_text.split(" ")[0])

        aom_params_text = self.widgets.aom_params.text().strip()

        settings = AOMAV1Settings(
            usage=self.widgets.usage.currentText(),
            cpu_used=self.widgets.cpu_used.currentText(),
            row_mt=self.widgets.row_mt.currentText(),
            tune=self.widgets.tune.currentText(),
            aq_mode=self.widgets.aq_mode.currentText().split(" ")[0],
            tile_rows=self.widgets.tile_rows.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            denoise_noise_level=denoise_noise_level,
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            aom_params=aom_params_text.split(":") if aom_params_text else [],
        )
        encode_type, q_value = self.get_mode_settings()
        settings.crf = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
