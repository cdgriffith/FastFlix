#!/usr/bin/env python
import os
from pathlib import Path
import logging

from flix import ff_version, Flix
from flix.shared import QtWidgets

logger = logging.getLogger('flix')

__all__ = ['Settings']


class Settings(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent)
        self.main = parent
        layout = QtWidgets.QGridLayout()

        self.warning_message = QtWidgets.QLabel("")
        self.warning_message.setFixedHeight(40)

        # Buttons
        self.button_group = QtWidgets.QButtonGroup()

        self.env_radio = QtWidgets.QRadioButton("Environment Variables (FFMPEG and FFPROBE)")
        self.path_radio = QtWidgets.QRadioButton("System PATH")
        self.binary_radio = QtWidgets.QRadioButton("Direct path to binaries")
        self.env_radio.name = "env"
        self.path_radio.name = "path"
        self.binary_radio.name = "binary"

        self.button_group.addButton(self.env_radio)
        self.button_group.addButton(self.path_radio)
        self.button_group.addButton(self.binary_radio)

        self.button_group.buttonClicked.connect(self.choice)

        # Path Select

        self.binary_select = QtWidgets.QGroupBox("Binaries")
        self.binary_select.setCheckable(False)
        self.binary_select.setDisabled(True)
        self.binary_select.setFixedHeight(120)

        binary_file_box = QtWidgets.QVBoxLayout()
        binary_file_layout = QtWidgets.QHBoxLayout()
        self.binary_file_path = QtWidgets.QLineEdit()
        self.binary_file_path.setReadOnly(True)
        self.binary_file_path.setText(os.getcwd())
        self.open_binary_file = QtWidgets.QPushButton("...")
        self.binary_file_info = QtWidgets.QLabel("")
        binary_file_layout.addWidget(QtWidgets.QLabel("Binary directory:"))
        binary_file_layout.addWidget(self.binary_file_path)
        binary_file_layout.addWidget(self.open_binary_file)
        binary_file_layout.setSpacing(20)
        self.open_binary_file.clicked.connect(self.open_binary_dir)
        binary_file_box.addLayout(binary_file_layout)
        binary_file_box.addWidget(self.binary_file_info)
        self.binary_select.setLayout(binary_file_box)

        layout.addWidget(self.warning_message, 0, 0)
        layout.addWidget(self.env_radio, 1, 0)
        layout.addWidget(self.path_radio, 2, 0)
        layout.addWidget(self.binary_radio, 3, 0)
        layout.addWidget(self.binary_select, 4, 0)
        layout.addWidget(QtWidgets.QLabel(), 5, 0, 4, 2)

        self.setLayout(layout)
        self.check()

    def choice(self, x):
        self.binary_select.setDisabled(x.name != "binary")
        if x.name == 'env':
            self.env()
        if x.name == 'binary':
            self.check_dir(self.binary_file_path.text())
        if x.name == 'path':
            self.path()
        self.check()

    def path(self):
        self.main.ffmpeg = 'ffmpeg'
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = 'ffprobe'
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def env(self):
        self.main.ffmpeg = os.getenv('FFMPEG')
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = os.getenv('FFPROBE')
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def check_dir(self, directory):
        updated_ffmpeg, updated_ffprobe = False, False
        for path in Path(directory).iterdir():
            if path.stem == 'ffmpeg':
                ffmpeg_ver = ff_version(path, throw=False)
                if ffmpeg_ver:
                    self.main.ffmpeg = str(path)
                    self.main.ffmpeg_version = ffmpeg_ver
                    updated_ffmpeg = True
            if path.stem == 'ffprobe':
                ffprobe_ver = ff_version(path, throw=False)
                if ffprobe_ver:
                    self.main.ffprobe = str(path)
                    self.main.ffprobe_version = ffprobe_ver
                    updated_ffprobe = True
        warnings = []
        if not updated_ffmpeg:
            warnings.append("Did not find FFMPEG binary in this directory!")
        if not updated_ffprobe:
            warnings.append("Did not find FFPROBE binary in this directory!")
        if warnings:
            warnings.append("Please make sure the files are only named ffmpeg (or ffmpeg.exe) "
                            "and ffprobe (or ffprobe.exe)")
            self.binary_file_info.setText("<br>".join(warnings))
        else:
            self.binary_file_info.setText("Binary files found!")

    def open_binary_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if not directory:
            self.path_radio.setChecked(True)
            self.binary_select.setDisabled(True)
        self.binary_file_path.setText(str(directory))
        self.check_dir(directory)
        self.check()

    def check(self):
        if self.main.ffmpeg_version and self.main.ffprobe_version:
            self.warning_message.setText("<b>Status:</b> Everything is under control. Situation normal.")
            self.main.enable_converters()
            if 'libx265' not in Flix(ffmpeg=self.main.ffmpeg).ffmpeg_configuration():
                self.main.disable_converters('x265')
        elif self.main.ffmpeg_version:
            self.warning_message.setText("<b>Status:</b> ffprobe not found")
            self.main.disable_converters()
        elif self.main.ffprobe_version:
            self.warning_message.setText("<b>Status:</b> ffmpeg not found")
            self.main.disable_converters()
        else:
            self.warning_message.setText("<b>Status:</b> ffmpeg and ffprobe not found")
            self.main.disable_converters()
        self.main.default_status()
        if self.main.ffmpeg_version:
            logger.debug(f"ffmpeg version: {self.main.ffmpeg_version}")
        if self.main.ffprobe_version:
            logger.debug(f"ffprobe version: {self.main.ffprobe_version}")
