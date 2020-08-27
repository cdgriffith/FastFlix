# -*- coding: utf-8 -*-

import shutil
from pathlib import Path

from box import Box

from qtpy import QtWidgets, QtCore, QtGui

from fastflix.shared import error_message


class Settings(QtWidgets.QWidget):
    def __init__(self, config_file, main_app, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.config_file = config_file
        self.main_app = main_app
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 200)
        layout = QtWidgets.QGridLayout()

        ffmpeg_label = QtWidgets.QLabel("FFmpeg")
        self.ffmpeg_path = QtWidgets.QLineEdit()
        self.ffmpeg_path.setText(str(self.main_app.ffmpeg))
        # self.ffmpeg_path.textChanged.connect(lambda: self.update_ffmpeg)
        layout.addWidget(ffmpeg_label, 0, 0)
        layout.addWidget(self.ffmpeg_path, 0, 1)

        # TODO change to  QtWidgets.QFileDialog
        ffprobe_label = QtWidgets.QLabel("FFprobe")
        self.ffprobe_path = QtWidgets.QLineEdit()
        self.ffprobe_path.setText(str(self.main_app.ffprobe))
        # self.ffprobe_path.textChanged.connect(lambda: self.update_ffprobe)
        layout.addWidget(ffprobe_label, 1, 0)
        layout.addWidget(self.ffprobe_path, 1, 1)

        work_dir_label = QtWidgets.QLabel("Work Directory")
        self.work_dir = QtWidgets.QLineEdit()
        self.work_dir.setText(str(self.main_app.path.work))
        # self.ffprobe_path.textChanged.connect(lambda: self.update_ffprobe)
        layout.addWidget(work_dir_label, 2, 0)
        layout.addWidget(self.work_dir, 2, 1)

        svt_av1_label = QtWidgets.QLabel("SVT AV1")
        self.svt_av1_path = QtWidgets.QLineEdit()
        self.svt_av1_path.setText(str(self.main_app.svt_av1) if self.main_app.svt_av1 else "")
        # self.ffprobe_path.textChanged.connect(lambda: self.update_ffprobe)
        layout.addWidget(svt_av1_label, 3, 0)
        layout.addWidget(self.svt_av1_path, 3, 1)

        save = QtWidgets.QPushButton(text="Save")
        save.clicked.connect(lambda: self.save())

        cancel = QtWidgets.QPushButton(text="Cancel")
        cancel.clicked.connect(lambda: self.close())

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(save)

        layout.addLayout(button_layout, 10, 0, 1, 3)

        self.setLayout(layout)

    def save(self):
        new_ffmpeg = Path(self.ffmpeg_path.text())
        new_ffprobe = Path(self.ffprobe_path.text())
        new_work_dir = Path(self.work_dir.text())
        new_svt_av1 = Path(self.svt_av1_path.text())
        self.update_ffmpeg(new_ffmpeg)
        self.update_ffprobe(new_ffprobe)
        self.update_svt_av1(new_svt_av1)

        try:
            new_work_dir.mkdir(exist_ok=True, parents=True)
        except OSError:
            error_message(f'Could not create / access work directory "{new_work_dir}"')
        else:
            self.update_setting("work_dir", new_work_dir)
            self.main_app.path.work = new_work_dir

    def update_ffmpeg(self, new_path):
        if self.main_app.ffmpeg == new_path:
            return
        if not new_path.exists():
            if not shutil.which(str(new_path)):
                error_message(f"No FFmpeg instance found at {new_path}, not updated")
                return
        self.update_setting("ffmpeg", str(new_path))
        self.main_app.ffmpeg = new_path

    def update_ffprobe(self, new_path):
        if self.main_app.ffprobe == new_path:
            return
        if not new_path.exists():
            if not shutil.which(str(new_path)):
                error_message(f"No FFprobe instance found at {new_path}, not updated")
                return
        self.update_setting("ffprobe", str(new_path))
        self.main_app.ffprobe = new_path

    def update_svt_av1(self, new_path):
        if self.main_app.svt_av1 == new_path:
            return
        if new_path and not new_path.exists():
            if not shutil.which(str(new_path)):
                error_message(f"No SVT AV1 instance found at {new_path}, not updated")
                return
        self.update_setting("svt_av1", str(new_path))
        self.main_app.svt_av1 = new_path

    def update_setting(self, name, value):
        mappings = {
            "version": "version",
            "work_dir": "work_dir",
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
            "svt_av1": "svt_av1",
        }

        settings = Box(box_dots=True).from_json(filename=self.config_file)
        settings[mappings[name]] = value
        settings.to_json(filename=self.config_file)
