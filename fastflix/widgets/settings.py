# -*- coding: utf-8 -*-

import shutil
from pathlib import Path

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

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
        ffmpeg_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffmpeg_path_button.clicked.connect(lambda: self.select_ffmpeg())
        layout.addWidget(ffmpeg_label, 0, 0)
        layout.addWidget(self.ffmpeg_path, 0, 1)
        layout.addWidget(ffmpeg_path_button, 0, 2)

        ffprobe_label = QtWidgets.QLabel("FFprobe")
        self.ffprobe_path = QtWidgets.QLineEdit()
        self.ffprobe_path.setText(str(self.main_app.ffprobe))
        ffprobe_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffprobe_path_button.clicked.connect(lambda: self.select_ffprobe())
        layout.addWidget(ffprobe_label, 1, 0)
        layout.addWidget(self.ffprobe_path, 1, 1)
        layout.addWidget(ffprobe_path_button, 1, 2)

        work_dir_label = QtWidgets.QLabel("Work Directory")
        self.work_dir = QtWidgets.QLineEdit()
        self.work_dir.setText(str(self.main_app.path.work))
        work_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        work_path_button.clicked.connect(lambda: self.select_work_path())
        layout.addWidget(work_dir_label, 2, 0)
        layout.addWidget(self.work_dir, 2, 1)
        layout.addWidget(work_path_button, 2, 2)

        layout.addWidget(QtWidgets.QLabel("Config File"), 4, 0)
        layout.addWidget(QtWidgets.QLabel(str(self.config_file)), 4, 1)

        save = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton), text="Save")
        save.clicked.connect(lambda: self.save())

        cancel = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton), text="Cancel"
        )
        cancel.clicked.connect(lambda: self.close())

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(QtWidgets.QLabel("A FastFlix restart is required to apply changes"))
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(save)

        layout.addLayout(button_layout, 10, 0, 1, 3)

        self.setLayout(layout)

    def save(self):
        new_ffmpeg = Path(self.ffmpeg_path.text())
        new_ffprobe = Path(self.ffprobe_path.text())
        new_work_dir = Path(self.work_dir.text())
        errors = bool(self.update_ffmpeg(new_ffmpeg))
        errors |= bool(self.update_ffprobe(new_ffprobe))

        try:
            new_work_dir.mkdir(exist_ok=True, parents=True)
        except OSError:
            error_message(f'Could not create / access work directory "{new_work_dir}"')
        else:
            self.update_setting("work_dir", new_work_dir)
            self.main_app.path.work = new_work_dir
        if not errors:
            self.close()

    def select_ffmpeg(self):
        dirname = Path(self.ffmpeg_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="FFmepg location", directory=str(dirname))
        if not filename or not filename[0]:
            return
        self.ffmpeg_path.setText(filename[0])

    @staticmethod
    def path_check(name, new_path):
        if not new_path.exists():
            which = shutil.which(str(new_path))
            if not which:
                error_message(f"No {name} instance found at {new_path}, not updated")
                return
            return Path(which)
        if not new_path.is_file():
            error_message(f"{new_path} is not a file")
            return
        return new_path

    def update_ffmpeg(self, new_path):
        if self.main_app.ffmpeg == new_path:
            return
        new_path = self.path_check("FFmpeg", new_path)
        if not new_path:
            return True
        self.update_setting("ffmpeg", str(new_path))
        self.main_app.ffmpeg = new_path

    def select_ffprobe(self):
        dirname = Path(self.ffprobe_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="FFprobe location", directory=str(dirname))
        if not filename or not filename[0]:
            return
        self.ffprobe_path.setText(filename[0])

    def update_ffprobe(self, new_path):
        if self.main_app.ffprobe == new_path:
            return
        new_path = self.path_check("FFprobe", new_path)
        if not new_path:
            return True
        self.update_setting("ffprobe", str(new_path))
        self.main_app.ffprobe = new_path

    def select_work_path(self):
        dirname = Path(self.work_dir.text())
        if not dirname.exists():
            dirname = Path()
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly)
        work_path = dialog.getExistingDirectory(directory=str(dirname), caption="Work directory")
        if not work_path:
            return
        self.work_dir.setText(work_path)

    def update_setting(self, name, value):
        # TODO change work dir in main and create new temp folder
        mappings = {
            "work_dir": "work_dir",
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
        }

        settings = Box(box_dots=True).from_json(filename=self.config_file)
        old_settings = settings.copy()
        if value:
            settings[mappings[name]] = str(value)
        else:
            del settings[mappings[name]]
        try:
            settings.to_json(filename=self.config_file, indent=2)
        except Exception:
            old_settings.to_json(filename=self.config_file, indent=2)
            error_message("Could not update settings", traceback=True)
