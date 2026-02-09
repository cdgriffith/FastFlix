#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import link

logger = logging.getLogger("fastflix")

recommended_bitrates = [
    "150k   (320x240p @ 30fps)",
    "276k   (640x360p @ 30fps)",
    "512k   (640x480p @ 30fps)",
    "1024k  (1280x720p @ 30fps)",
    "1800k (1280x720p @ 60fps)",
    "1800k (1920x1080p @ 30fps)",
    "3000k (1920x1080p @ 60fps)",
    "6000k (2560x1440p @ 30fps)",
    "9000k (2560x1440p @ 60fps)",
    "12000k (3840x2160p @ 30fps)",
    "18000k (3840x2160p @ 60fps)",
    "Custom",
]

recommended_qp = [
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24 - recommended",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30 - standard",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    '50 - "I\'m just testing to see if this works"',
    "Custom",
]
pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le"]

film_grain_options = [
    "0 - Disabled",
    "4 - Animation",
    "6 - Light grain",
    "8 - Normal",
    "10 - Heavy grain",
    "15 - Very heavy",
    "Custom",
]


class SVT_AV1(SettingPanel):
    profile_name = "svt_av1"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.widgets = Box(fps=None, mode=None, segment_size=None)

        self.mode = "CRF"

        grid.addLayout(self.init_preset(), 0, 0, 1, 2)
        grid.addLayout(self.init_tune(), 1, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 4, 0, 1, 2)
        grid.addLayout(self.init_sc_detection(), 5, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 6, 0, 1, 2)
        grid.addLayout(self.init_qp_or_crf(), 7, 0, 1, 2)
        grid.addLayout(self.init_sharpness(), 8, 0, 1, 2)
        grid.addLayout(self.init_fast_decode(), 9, 0, 1, 2)
        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self.init_film_grain(), 5, 2, 1, 4)
        grid.addLayout(self.init_film_grain_denoise(), 6, 2, 1, 4)
        grid.addLayout(self.init_svtav1_params(), 7, 2, 1, 4)

        grid.setRowStretch(12, 1)
        guide_label = QtWidgets.QLabel(
            link(
                "https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/Ffmpeg.md",
                t("SVT-AV1 Encoding Guide"),
                app.fastflix.config.theme,
            )
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addLayout(self._add_custom(), 14, 0, 1, 6)
        grid.addWidget(guide_label, 15, 0, -1, 1)
        self.setLayout(grid)
        self.hide()

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Break the video into rows to encode faster (lesser quality)",
            options=[str(x) for x in range(0, 7)],
            widget_name="tile_rows",
            opt="tile_rows",
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Break the video into columns to encode faster (lesser quality)",
            options=[str(x) for x in range(0, 5)],
            widget_name="tile_columns",
            opt="tile_columns",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_sc_detection(self):
        return self._add_combo_box(
            label="Scene Detection", options=["false", "true"], widget_name="sc_detection", opt="scene_detection"
        )

    # def init_single_pass(self):
    #     return self._add_check_box(
    #         label="Single Pass",
    #         widget_name="single_pass",
    #         tooltip="Single Pass Encoding",
    #         opt="single_pass",
    #     )

    def init_preset(self):
        return self._add_combo_box(
            label="Preset",
            widget_name="speed",
            options=[str(x) for x in range(14)],
            tooltip="Quality/Speed ratio modifier",
            opt="speed",
        )

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            widget_name="tune",
            options=["0 - VQ (Psychovisual)", "1 - PSNR", "2 - SSIM"],
            tooltip="Optimize encoding for different quality metrics",
            opt="tune",
        )

    def init_sharpness(self):
        return self._add_combo_box(
            label="Sharpness",
            widget_name="sharpness",
            options=[str(x) for x in range(-7, 8)],
            tooltip="Deblocking loop filter sharpness (-7 to 7, 0=default)",
            opt="sharpness",
        )

    def init_fast_decode(self):
        return self._add_combo_box(
            label="Fast Decode",
            widget_name="fast_decode",
            options=["0 - Disabled", "1 - Level 1", "2 - Level 2"],
            tooltip="Tune settings for faster decoding at the cost of quality",
            opt="fast_decode",
        )

    def init_film_grain(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.film_grain = QtWidgets.QLabel(t("Film Grain"))
        self.labels.film_grain.setFixedWidth(200)
        self.labels.film_grain.setToolTip(t("Film grain synthesis level (0=off, higher=more grain)"))
        layout.addWidget(self.labels.film_grain)
        self.widgets.film_grain = QtWidgets.QComboBox()
        self.widgets.film_grain.addItems(film_grain_options)
        self.widgets.film_grain.setToolTip(t("Film grain synthesis level (0=off, higher=more grain)"))
        self.widgets.film_grain.currentIndexChanged.connect(lambda: self.film_grain_update())
        self.opts["film_grain"] = "film_grain"
        layout.addWidget(self.widgets.film_grain)
        self.widgets.custom_film_grain = QtWidgets.QLineEdit()
        self.widgets.custom_film_grain.setFixedWidth(60)
        self.widgets.custom_film_grain.setDisabled(True)
        self.widgets.custom_film_grain.setToolTip(t("Custom film grain value (0-50)"))
        self.widgets.custom_film_grain.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.custom_film_grain)

        saved = self.app.fastflix.config.encoder_opt(self.profile_name, "film_grain")
        if saved and str(saved) != "0":
            matched = False
            for i, opt in enumerate(film_grain_options):
                if opt.startswith(str(saved)):
                    self.widgets.film_grain.setCurrentIndex(i)
                    matched = True
                    break
            if not matched:
                self.widgets.film_grain.setCurrentIndex(len(film_grain_options) - 1)
                self.widgets.custom_film_grain.setText(str(saved))

        return layout

    def film_grain_update(self):
        custom = self.widgets.film_grain.currentText() == "Custom"
        self.widgets.custom_film_grain.setDisabled(not custom)
        self.main.page_update()

    def init_film_grain_denoise(self):
        return self._add_check_box(
            label="Film Grain Denoise",
            widget_name="film_grain_denoise",
            tooltip="Apply denoising when film grain is enabled",
            opt="film_grain_denoise",
        )

    def init_qp_or_crf(self):
        return self._add_combo_box(
            label="Quantization Mode",
            widget_name="qp_mode",
            options=["crf", "qp"],
            tooltip="Use CRF or QP",
            opt="qp_mode",
        )

    def init_svtav1_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.svtav1_params = QtWidgets.QLabel(t("Additional svt av1 params"))
        self.labels.svtav1_params.setFixedWidth(200)
        tool_tip = f"{t('Extra svt av1 params in opt=1:opt2=0 format')},\n{t('cannot modify generated settings')}"
        self.labels.svtav1_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.svtav1_params)
        self.widgets.svtav1_params = QtWidgets.QLineEdit()
        self.widgets.svtav1_params.setToolTip(tool_tip)
        self.widgets.svtav1_params.setText(
            ":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "svtav1_params"))
        )
        self.opts["svtav1_params"] = "svtav1_params"
        self.widgets.svtav1_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.svtav1_params)
        return layout

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_qp, qp_name="qp", qp_display_name="CRF/QP")

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        svtav1_params_text = self.widgets.svtav1_params.text().strip()

        # Parse film grain value from combo box or custom field
        film_grain_text = self.widgets.film_grain.currentText()
        if film_grain_text == "Custom":
            try:
                film_grain = int(self.widgets.custom_film_grain.text())
            except (ValueError, TypeError):
                film_grain = 0
        else:
            film_grain = int(film_grain_text.split(" ")[0])

        settings = SVTAV1Settings(
            speed=self.widgets.speed.currentText(),
            tune=self.widgets.tune.currentText().split(" ")[0],
            tile_columns=self.widgets.tile_columns.currentText(),
            tile_rows=self.widgets.tile_rows.currentText(),
            single_pass=True,
            scene_detection=bool(self.widgets.sc_detection.currentIndex()),
            qp_mode=self.widgets.qp_mode.currentText(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            film_grain=film_grain,
            film_grain_denoise=self.widgets.film_grain_denoise.isChecked(),
            sharpness=self.widgets.sharpness.currentText(),
            fast_decode=self.widgets.fast_decode.currentText().split(" ")[0],
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            svtav1_params=svtav1_params_text.split(":") if svtav1_params_text else [],
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
