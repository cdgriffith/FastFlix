# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
import logging

from box import Box
from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import error_message
from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t, change_language

logger = logging.getLogger("fastflix")
language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())


class Settings(QtWidgets.QWidget):
    def __init__(self, app: FastFlixApp, main, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.app = app
        self.main = main
        self.config_file = self.app.fastflix.config.config_path
        self.setWindowTitle(t("Settings"))
        self.setMinimumSize(600, 200)
        layout = QtWidgets.QGridLayout()

        ffmpeg_label = QtWidgets.QLabel("FFmpeg")
        self.ffmpeg_path = QtWidgets.QLineEdit()
        self.ffmpeg_path.setText(str(self.app.fastflix.config.ffmpeg))
        ffmpeg_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffmpeg_path_button.clicked.connect(lambda: self.select_ffmpeg())
        layout.addWidget(ffmpeg_label, 0, 0)
        layout.addWidget(self.ffmpeg_path, 0, 1)
        layout.addWidget(ffmpeg_path_button, 0, 2)

        ffprobe_label = QtWidgets.QLabel("FFprobe")
        self.ffprobe_path = QtWidgets.QLineEdit()
        self.ffprobe_path.setText(str(self.app.fastflix.config.ffprobe))
        ffprobe_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        ffprobe_path_button.clicked.connect(lambda: self.select_ffprobe())
        layout.addWidget(ffprobe_label, 1, 0)
        layout.addWidget(self.ffprobe_path, 1, 1)
        layout.addWidget(ffprobe_path_button, 1, 2)

        work_dir_label = QtWidgets.QLabel(t("Work Directory"))
        self.work_dir = QtWidgets.QLineEdit()
        self.work_dir.setText(str(self.app.fastflix.config.work_path))
        work_path_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        work_path_button.clicked.connect(lambda: self.select_work_path())
        layout.addWidget(work_dir_label, 2, 0)
        layout.addWidget(self.work_dir, 2, 1)
        layout.addWidget(work_path_button, 2, 2)

        layout.addWidget(QtWidgets.QLabel("Config File"), 4, 0)
        layout.addWidget(QtWidgets.QLabel(str(self.config_file)), 4, 1)

        self.language_combo = QtWidgets.QComboBox(self)
        self.language_combo.addItems(language_list)
        try:
            index = language_list.index(Lang(self.app.fastflix.config.language).name)
        except (IndexError, InvalidLanguageValue):
            logger.exception(f"Could not find language for {self.app.fastflix.config.language}")
            index = language_list.index("English")
        self.language_combo.setCurrentIndex(index)

        layout.addWidget(QtWidgets.QLabel(t("Language")), 5, 0)
        layout.addWidget(self.language_combo, 5, 1)

        config_button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
        config_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.config_file)))
        )
        layout.addWidget(config_button, 4, 2)

        save = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton), text="Save")
        save.clicked.connect(lambda: self.save())

        cancel = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton), text="Cancel"
        )
        cancel.clicked.connect(lambda: self.close())

        self.use_sane_audio = QtWidgets.QCheckBox("Use Sane Audio Selection (updatable in config file)")
        if self.app.fastflix.config.use_sane_audio:
            self.use_sane_audio.setChecked(True)
        self.disable_version_check = QtWidgets.QCheckBox("Disable update check on startup")
        if not self.app.fastflix.config.disable_version_check:
            self.disable_version_check.setChecked(False)
        elif self.app.fastflix.config.disable_version_check:
            self.disable_version_check.setChecked(True)

        layout.addWidget(self.use_sane_audio, 7, 0, 1, 2)
        layout.addWidget(self.disable_version_check, 8, 0, 1, 2)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(save)

        layout.addLayout(button_layout, 11, 0, 1, 3)

        self.setLayout(layout)

    def save(self):
        new_ffmpeg = Path(self.ffmpeg_path.text())
        new_ffprobe = Path(self.ffprobe_path.text())
        new_work_dir = Path(self.work_dir.text())
        try:
            updated_ffmpeg = self.update_ffmpeg(new_ffmpeg)
            self.update_ffprobe(new_ffprobe)
        except FastFlixInternalException:
            return

        try:
            new_work_dir.mkdir(exist_ok=True, parents=True)
        except OSError:
            error_message(f'Could not create / access work directory "{new_work_dir}"')
        else:
            self.app.fastflix.config.work_path = new_work_dir
        self.app.fastflix.config.use_sane_audio = self.use_sane_audio.isChecked()
        try:
            self.app.fastflix.config.language = Lang(self.language_combo.currentText()).pt2b
        except InvalidLanguageValue:
            error_message(f"Could not set language to {self.language_combo.currentText()}\n Please report this issue")
        else:
            change_language(self.app.fastflix.config.language)
        self.app.fastflix.config.disable_version_check = self.disable_version_check.isChecked()

        self.main.config_update()
        self.app.fastflix.config.save()
        if updated_ffmpeg:
            error_message(t("FFmpeg updated - Please restart FastFlix"))
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
                raise FastFlixInternalException(f"No {name} instance found at {new_path}, not updated")
            return Path(which)
        if not new_path.is_file():
            error_message(f"{new_path} is not a file")
            raise FastFlixInternalException(f"No {name} instance found at {new_path}, not updated")
        return new_path

    def update_ffmpeg(self, new_path):
        if self.app.fastflix.config.ffmpeg == new_path:
            return False
        new_path = self.path_check("FFmpeg", new_path)
        self.app.fastflix.config.ffmpeg = new_path
        self.update_setting("ffmpeg", str(new_path))
        return True

    def select_ffprobe(self):
        dirname = Path(self.ffprobe_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="FFprobe location", directory=str(dirname))
        if not filename or not filename[0]:
            return
        self.ffprobe_path.setText(filename[0])

    def update_ffprobe(self, new_path):
        if self.app.fastflix.config.ffprobe == new_path:
            return False
        new_path = self.path_check("FFprobe", new_path)
        self.app.fastflix.config.ffprobe = new_path
        self.update_setting("ffprobe", str(new_path))
        return True

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
        setattr(self.app.fastflix.config, name, value)
