#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from PySide6 import QtCore, QtWidgets

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import rav1eSettings
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
    "60 - high quality",
    "70",
    "80 - recommended",
    "90",
    "100 - rav1e default",
    "110",
    "120",
    "140",
    '200 - "I\'m just testing to see if this works"',
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

photon_noise_options = [
    "0 - Disabled",
    "4 - Light",
    "8 - Normal",
    "16 - Heavy",
    "32 - Very heavy",
    "Custom",
]


class RAV1E(SettingPanel):
    profile_name = "rav1e"

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app

        grid = QtWidgets.QGridLayout()

        self.mode = "QP"

        grid.addLayout(self.init_speed(), 0, 0, 1, 2)
        grid.addLayout(self.init_tune(), 1, 0, 1, 2)
        grid.addLayout(self.init_tiles(), 2, 0, 1, 2)
        grid.addLayout(self.init_tile_rows(), 3, 0, 1, 2)
        grid.addLayout(self.init_tile_columns(), 4, 0, 1, 2)
        grid.addLayout(self.init_pix_fmt(), 5, 0, 1, 2)
        grid.addLayout(self.init_sc_detection(), 6, 0, 1, 2)
        grid.addLayout(self.init_max_mux(), 7, 0, 1, 2)

        grid.addLayout(self.init_modes(), 0, 2, 5, 4)
        grid.addLayout(self.init_single_pass(), 5, 2, 1, 1)
        grid.addLayout(self.init_photon_noise(), 6, 2, 1, 4)
        grid.addLayout(self.init_rav1e_params(), 7, 2, 1, 4)

        grid.addLayout(self._add_custom(), 10, 0, 1, 6)

        grid.setRowStretch(9, 1)
        guide_label = QtWidgets.QLabel(
            link("https://github.com/xiph/rav1e/blob/master/README.md", t("rav1e github"), app.fastflix.config.theme)
        )
        guide_label.setAlignment(QtCore.Qt.AlignBottom)
        guide_label.setOpenExternalLinks(True)
        grid.addWidget(guide_label, 11, 0, 1, 6)
        self.setLayout(grid)
        self.hide()

    def init_speed(self):
        return self._add_combo_box(
            label="Speed",
            tooltip="Quality/Speed ratio modifier (defaults to -1)",
            options=[str(x) for x in range(-1, 11)],
            widget_name="speed",
            opt="speed",
        )

    def init_tune(self):
        return self._add_combo_box(
            label="Tune",
            tooltip="Quality tuning metric (Psychovisual for perceptual quality, Psnr for objective quality)",
            widget_name="tune",
            options=["default", "Psychovisual", "Psnr"],
            opt="tune",
        )

    def init_tile_rows(self):
        return self._add_combo_box(
            label="Tile Rows",
            tooltip="Break the video into rows to encode faster (lesser quality)",
            options=[str(x) for x in range(-1, 17)],
            widget_name="tile_rows",
            opt="tile_rows",
        )

    def init_tile_columns(self):
        return self._add_combo_box(
            label="Tile Columns",
            tooltip="Break the video into columns to encode faster (lesser quality)",
            options=[str(x) for x in range(-1, 17)],
            widget_name="tile_columns",
            opt="tile_columns",
        )

    def init_tiles(self):
        return self._add_combo_box(
            label="Tiles", options=[str(x) for x in range(-1, 17)], widget_name="tiles", opt="tiles"
        )

    def init_single_pass(self):
        return self._add_check_box(label="Single Pass (Bitrate)", widget_name="single_pass", opt="single_pass")

    def init_sc_detection(self):
        return self._add_combo_box(
            label="Scene Detection",
            tooltip="Enable scene detection for better keyframe placement",
            options=["true", "false"],
            widget_name="sc_detection",
            opt="scene_detection",
        )

    def init_pix_fmt(self):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=pix_fmts,
            opt="pix_fmt",
        )

    def init_photon_noise(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.photon_noise = QtWidgets.QLabel(t("Photon Noise"))
        self.labels.photon_noise.setFixedWidth(200)
        self.labels.photon_noise.setToolTip(t("Film grain synthesis strength (0=off, higher=more grain)"))
        layout.addWidget(self.labels.photon_noise)
        self.widgets.photon_noise = QtWidgets.QComboBox()
        self.widgets.photon_noise.addItems(photon_noise_options)
        self.widgets.photon_noise.setToolTip(t("Film grain synthesis strength (0=off, higher=more grain)"))
        self.widgets.photon_noise.currentIndexChanged.connect(lambda: self.photon_noise_update())
        self.opts["photon_noise"] = "photon_noise"
        layout.addWidget(self.widgets.photon_noise)
        self.widgets.custom_photon_noise = QtWidgets.QLineEdit()
        self.widgets.custom_photon_noise.setFixedWidth(60)
        self.widgets.custom_photon_noise.setDisabled(True)
        self.widgets.custom_photon_noise.setToolTip(t("Custom photon noise value (0-64)"))
        self.widgets.custom_photon_noise.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.custom_photon_noise)

        saved = self.app.fastflix.config.encoder_opt(self.profile_name, "photon_noise")
        if saved and str(saved) != "0":
            matched = False
            for i, opt in enumerate(photon_noise_options):
                if opt.startswith(str(saved)):
                    self.widgets.photon_noise.setCurrentIndex(i)
                    matched = True
                    break
            if not matched:
                self.widgets.photon_noise.setCurrentIndex(len(photon_noise_options) - 1)
                self.widgets.custom_photon_noise.setText(str(saved))

        return layout

    def photon_noise_update(self):
        custom = self.widgets.photon_noise.currentText() == "Custom"
        self.widgets.custom_photon_noise.setDisabled(not custom)
        self.main.page_update()

    def init_rav1e_params(self):
        layout = QtWidgets.QHBoxLayout()
        self.labels.rav1e_params = QtWidgets.QLabel(t("Additional rav1e params"))
        self.labels.rav1e_params.setFixedWidth(200)
        tool_tip = f"{t('Extra rav1e params in opt=1:opt2=0 format')},\n{t('cannot modify generated settings')}"
        self.labels.rav1e_params.setToolTip(tool_tip)
        layout.addWidget(self.labels.rav1e_params)
        self.widgets.rav1e_params = QtWidgets.QLineEdit()
        self.widgets.rav1e_params.setToolTip(tool_tip)
        self.widgets.rav1e_params.setText(
            ":".join(self.app.fastflix.config.encoder_opt(self.profile_name, "rav1e_params"))
        )
        self.opts["rav1e_params"] = "rav1e_params"
        self.widgets.rav1e_params.textChanged.connect(lambda: self.main.page_update())
        layout.addWidget(self.widgets.rav1e_params)
        return layout

    def init_modes(self):
        return self._add_modes(recommended_bitrates, recommended_qp, qp_name="qp")

    def mode_update(self):
        self.widgets.custom_qp.setDisabled(self.widgets.qp.currentText() != "Custom")
        self.widgets.custom_bitrate.setDisabled(self.widgets.bitrate.currentText() != "Custom")
        self.main.build_commands()

    def update_video_encoder_settings(self):
        # Parse photon noise value from combo box or custom field
        photon_noise_text = self.widgets.photon_noise.currentText()
        if photon_noise_text == "Custom":
            try:
                photon_noise = int(self.widgets.custom_photon_noise.text())
            except (ValueError, TypeError):
                photon_noise = 0
        else:
            photon_noise = int(photon_noise_text.split(" ")[0])

        rav1e_params_text = self.widgets.rav1e_params.text().strip()

        settings = rav1eSettings(
            speed=self.widgets.speed.currentText(),
            tune=self.widgets.tune.currentText(),
            tile_columns=self.widgets.tile_columns.currentText(),
            tile_rows=self.widgets.tile_rows.currentText(),
            tiles=self.widgets.tiles.currentText(),
            single_pass=self.widgets.single_pass.isChecked(),
            scene_detection=bool(self.widgets.sc_detection.currentIndex() == 0),
            photon_noise=photon_noise,
            max_muxing_queue_size=self.widgets.max_mux.currentText(),
            extra=self.ffmpeg_extras,
            extra_both_passes=self.widgets.extra_both_passes.isChecked(),
            pix_fmt=self.widgets.pix_fmt.currentText().split(":")[1].strip(),
            rav1e_params=rav1e_params_text.split(":") if rav1e_params_text else [],
        )
        encode_type, q_value = self.get_mode_settings()
        settings.qp = q_value if encode_type == "qp" else None
        settings.bitrate = q_value if encode_type == "bitrate" else None
        self.app.fastflix.current_video.video_settings.video_encoder_settings = settings

    def set_mode(self, x):
        self.mode = x.text()
        self.main.build_commands()
