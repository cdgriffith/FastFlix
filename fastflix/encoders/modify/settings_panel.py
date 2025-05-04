# -*- coding: utf-8 -*-
import logging
import os
from pathlib import Path

from PySide6 import QtWidgets, QtGui, QtCore

from fastflix.encoders.common.setting_panel import SettingPanel
from fastflix.language import t
from fastflix.models.encode import ModifySettings
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import message, yes_no_message
from fastflix.widgets.background_tasks import AudioNoramlize
from fastflix.resources import loading_movie, get_icon

logger = logging.getLogger("fastflix")


class Modify(SettingPanel):
    profile_name = "modify_settings"
    signal = QtCore.Signal(str)

    def __init__(self, parent, main, app: FastFlixApp):
        super().__init__(parent, main, app)
        self.main = main
        self.app = app
        self.signal.connect(self.audio_norm_done)

        self.extract_label = QtWidgets.QLabel(self)
        self.extract_label.hide()
        self.movie = QtGui.QMovie(loading_movie)
        self.movie.setScaledSize(QtCore.QSize(25, 25))
        self.extract_label.setMovie(self.movie)

        grid = QtWidgets.QGridLayout()

        grid.addWidget(QtWidgets.QLabel(""), 1, 0)
        self.audio_normalize = QtWidgets.QPushButton(t("Run Audio Normalize"))
        self.audio_normalize.clicked.connect(self.select_run_audio_normalize)
        grid.addWidget(self.audio_normalize, 2, 0, 1, 1)
        grid.addWidget(self.extract_label, 2, 2, 1, 1)

        self.audio_format_combo = QtWidgets.QComboBox()
        self.audio_format_combo.addItems(self.app.fastflix.config.sane_audio_selection)
        grid.addWidget(self.audio_format_combo, 2, 1, 1, 1)

        add_audio_track = QtWidgets.QPushButton(t("Add Audio Track"))
        add_audio_track.clicked.connect(self.select_audio_file)
        self.add_audio_track_file_path = QtWidgets.QLineEdit()
        grid.addWidget(add_audio_track, 3, 0, 1, 1)
        grid.addWidget(self.add_audio_track_file_path, 3, 1, 1, 2)

        add_sub_track = QtWidgets.QPushButton(t("Add Text Based Subtitle Track"))
        add_sub_track.clicked.connect(self.select_subtitle_file)
        self.add_sub_track_file_path = QtWidgets.QLineEdit()
        grid.addWidget(add_sub_track, 4, 0, 1, 1)
        grid.addWidget(self.add_sub_track_file_path, 4, 1, 1, 2)

        grid.addWidget(QtWidgets.QWidget(), 6, 0, 6, 1)
        grid.addLayout(self._add_custom(disable_both_passes=True), 11, 0, 1, 6)
        self.setLayout(grid)
        self.hide()

    def update_video_encoder_settings(self):
        self.app.fastflix.current_video.video_settings.video_encoder_settings = ModifySettings(
            audio_normalize=self.audio_normalize.isChecked(),
            add_audio_track=self.add_audio_track_file_path.text() or None,
            add_subtitle_track=self.add_sub_track_file_path.text() or None,
        )
        self.app.fastflix.current_video.video_settings.video_encoder_settings.extra = self.ffmpeg_extras
        self.app.fastflix.current_video.video_settings.video_encoder_settings.extra_both_passes = False

    def select_audio_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, t("Select Audio Track"), "", t("Audio Files (*.mp3 *.aac *.wav *.flac);;All Files (*)")
        )
        if file_path:
            logger.info(f"Selected audio track: {file_path}")
            self.add_audio_track_file_path.setText(file_path)
        self.main.build_commands()

    def select_subtitle_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, t("Select Subtitle Track"), "", t("Subtitle Files (*.srt *.ass *.vtt *.ssa);;All Files (*)")
        )
        if file_path:
            logger.info(f"Selected subtitle track: {file_path}")
            self.add_sub_track_file_path.setText(file_path)
        self.main.build_commands()

    def select_run_audio_normalize(self):
        try:
            in_path = Path(self.app.fastflix.current_video.source)
            out_path = Path(self.app.fastflix.current_video.video_settings.output_path)
            assert in_path.exists()
            assert out_path.parent.exists()
        except Exception:
            message(t("Please make sure the source and output files are specified"))
            return

        audio_type = self.audio_format_combo.currentText()
        resp = yes_no_message(
            t("This will run the audio normalization process on all streams of")
            + f"\n{in_path}\n"
            + t("and create an output file with audio format ")
            + f"{audio_type}\n@ {out_path}\n",
            title="Audio Normalization",
        )
        if not resp:
            return
        self.norm_thread = AudioNoramlize(self.app, self.main, audio_type, self.signal)
        self.norm_thread.start()
        self.movie.start()
        self.extract_label.show()
        self.audio_normalize.setDisabled(True)

    def audio_norm_done(self, status):
        self.movie.stop()
        self.extract_label.hide()
        self.audio_normalize.setDisabled(False)
        message(f"Audio normalization done: {status}")
