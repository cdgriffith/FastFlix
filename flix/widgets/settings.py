#!/usr/bin/env python
import os
from pathlib import Path
import logging

from flix.flix import ff_version, Flix, svt_av1_version
from flix.shared import QtWidgets

logger = logging.getLogger('flix')

__all__ = ['Settings']


class Settings(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent)
        self.main = parent
        self.default_svt_av1 = self.main.svt_av1
        layout = QtWidgets.QGridLayout()
        self.ffmpeg_button = "path"
        self.svt_av1_button = "default"

        self.ffmpeg_warning_message = QtWidgets.QLabel("")
        self.ffmpeg_warning_message.setFixedHeight(40)

        # FFMPEG Buttons
        self.button_group = QtWidgets.QButtonGroup()

        self.env_radio = QtWidgets.QRadioButton("Environment Variables (FFMPEG and FFPROBE)")
        self.path_radio = QtWidgets.QRadioButton("System PATH")
        self.binary_radio = QtWidgets.QRadioButton("Direct path to binaries")
        self.env_radio.name = "env"
        self.path_radio.name = "path"
        self.binary_radio.name = "binary"
        self.path_radio.setChecked(True)

        self.button_group.addButton(self.env_radio)
        self.button_group.addButton(self.path_radio)
        self.button_group.addButton(self.binary_radio)

        self.button_group.buttonClicked.connect(self.fmpeg_choice)

        # FFMPEG Select

        self.ffmpeg_select = QtWidgets.QGroupBox("FFMPEG executable directory")
        self.ffmpeg_select.setCheckable(False)
        self.ffmpeg_select.setDisabled(True)
        self.ffmpeg_select.setFixedHeight(120)

        ffmpeg_file_box = QtWidgets.QVBoxLayout()
        ffmpeg_file_layout = QtWidgets.QHBoxLayout()
        self.ffmpeg_file_path = QtWidgets.QLineEdit()
        self.ffmpeg_file_path.setReadOnly(True)
        self.ffmpeg_file_path.setText(os.getcwd())
        self.open_ffmpeg_file = QtWidgets.QPushButton("...")
        self.ffmpeg_file_info = QtWidgets.QLabel("")
        ffmpeg_file_layout.addWidget(QtWidgets.QLabel("Binary directory:"))
        ffmpeg_file_layout.addWidget(self.ffmpeg_file_path)
        ffmpeg_file_layout.addWidget(self.open_ffmpeg_file)
        ffmpeg_file_layout.setSpacing(20)
        self.open_ffmpeg_file.clicked.connect(self.open_binary_dir)
        ffmpeg_file_box.addLayout(ffmpeg_file_layout)
        ffmpeg_file_box.addWidget(self.ffmpeg_file_info)
        self.ffmpeg_select.setLayout(ffmpeg_file_box)

        self.svt_av1_warning_message = QtWidgets.QLabel("")
        self.svt_av1_warning_message.setFixedHeight(40)

        # SVT_AV1 Buttons
        self.svt_av1_button_group = QtWidgets.QButtonGroup()

        self.svt_av1_default_radio = QtWidgets.QRadioButton("Default")
        self.svt_av1_env_radio = QtWidgets.QRadioButton("Environment Variable SVT_AV1")
        self.svt_av1_binary_radio = QtWidgets.QRadioButton("Direct path to executable")
        self.svt_av1_env_radio.name = "env"
        self.svt_av1_default_radio.name = "default"
        self.svt_av1_binary_radio.name = "binary"
        self.svt_av1_default_radio.setChecked(True)

        self.svt_av1_button_group.addButton(self.svt_av1_env_radio)
        self.svt_av1_button_group.addButton(self.svt_av1_default_radio)
        self.svt_av1_button_group.addButton(self.svt_av1_binary_radio)

        self.svt_av1_button_group.buttonClicked.connect(self.svt_av1_choice)

        # SVT_AV1 Select

        self.svt_av1_select = QtWidgets.QGroupBox("SVT-AV1 executable")
        self.svt_av1_select.setCheckable(False)
        self.svt_av1_select.setDisabled(True)
        self.svt_av1_select.setFixedHeight(60)

        svt_av1_file_box = QtWidgets.QVBoxLayout()
        svt_av1_file_layout = QtWidgets.QHBoxLayout()
        self.svt_av1_file_path = QtWidgets.QLineEdit()
        self.svt_av1_file_path.setReadOnly(True)
        self.svt_av1_file_path.setText(os.getcwd())
        self.open_svt_av1_file = QtWidgets.QPushButton("...")
        svt_av1_file_layout.addWidget(QtWidgets.QLabel("Executable:"))
        svt_av1_file_layout.addWidget(self.svt_av1_file_path)
        svt_av1_file_layout.addWidget(self.open_svt_av1_file)
        svt_av1_file_layout.setSpacing(20)
        self.open_svt_av1_file.clicked.connect(self.open_svt_av1_binary)
        svt_av1_file_box.addLayout(svt_av1_file_layout)
        self.svt_av1_select.setLayout(svt_av1_file_box)

        # SVT_AV1 Options

        self.svt_av1_save_segments = QtWidgets.QCheckBox("Save segments (for debug purposes)")
        self.svt_av1_save_segments.setChecked(False)

        self.svt_av1_save_raw_sections = QtWidgets.QCheckBox("Save raw sections (EXTREMELY LARGE FILES!)")
        self.svt_av1_save_raw_sections.setChecked(False)

        segment_layout = QtWidgets.QHBoxLayout()
        segment_label = QtWidgets.QLabel("Segment Length (seconds)")
        self.segment_size = QtWidgets.QLineEdit("60")
        segment_layout.addWidget(segment_label)
        segment_layout.addWidget(self.segment_size)

        layout.addWidget(self.ffmpeg_warning_message, 0, 0, 1, 4)

        layout.addWidget(self.path_radio, 1, 0)
        layout.addWidget(self.env_radio, 1, 1, 1, 2)
        layout.addWidget(self.binary_radio, 1, 4, 1, 1)

        layout.addWidget(self.ffmpeg_select, 2, 0, 1, 5)

        layout.addWidget(self.svt_av1_warning_message, 3, 0, 1, 4)

        layout.addWidget(self.svt_av1_env_radio, 4, 1, 1, 2)
        layout.addWidget(self.svt_av1_default_radio, 4, 0)
        layout.addWidget(self.svt_av1_binary_radio, 4, 4, 1, 1)

        layout.addWidget(self.svt_av1_select, 5, 0, 1, 5)

        layout.addLayout(segment_layout, 6, 0, 1, 2)

        layout.addWidget(self.svt_av1_save_segments, 7, 0, 1, 2)

        layout.addWidget(self.svt_av1_save_raw_sections, 8, 0, 1, 2)

        self.setLayout(layout)
        self.ffmpeg_check()
        self.check_svt_av1()

    def get_settings(self):
        try:
            segment_size = int(self.segment_size.text())
        except ValueError:
            segment_size = 60

        return {
            "svt_av1": {
                "path": self.main.svt_av1,
                "source_button": self.svt_av1_button,
                "save_segments": self.svt_av1_save_segments.isChecked(),
                "save_raw": self.svt_av1_save_raw_sections.isChecked(),
                "segment_size": segment_size
            },
            "ffmpeg": {
                "ffmpeg_path": self.main.ffmpeg,
                "ffprobe_path": self.main.ffprobe,
                "source_button": self.ffmpeg_button
            }
        }

    def fmpeg_choice(self, x):
        self.ffmpeg_button = x.name
        self.ffmpeg_select.setDisabled(x.name != "binary")
        if x.name == 'env':
            self.ffmpeg_env()
        if x.name == 'binary':
            self.check_ffmpeg_dir(self.ffmpeg_file_path.text())
        if x.name == 'path':
            self.ffmpeg_path()
        self.ffmpeg_check()

    def svt_av1_choice(self, x):
        self.svt_av1_button = x.name
        self.svt_av1_select.setDisabled(x.name != "binary")
        if x.name == 'env':
            self.svt_av1_env()
        if x.name == 'binary':
            self.main.svt_av1 = self.svt_av1_file_path.text()
        if x.name == 'default':
            self.svt_av1_path()
        self.check_svt_av1()

    def svt_av1_path(self):
        self.main.svt_av1 = self.default_svt_av1

    def svt_av1_env(self):
        self.main.svt_av1 = os.getenv('SVT_AV1')

    def ffmpeg_path(self):
        self.main.ffmpeg = 'ffmpeg'
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = 'ffprobe'
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def ffmpeg_env(self):
        self.main.ffmpeg = os.getenv('FFMPEG')
        self.main.ffmpeg_version = ff_version(self.main.ffmpeg, throw=False)
        self.main.ffprobe = os.getenv('FFPROBE')
        self.main.ffprobe_version = ff_version(self.main.ffprobe, throw=False)

    def check_svt_av1(self):
        file = Path(self.main.svt_av1)
        if not file.exists() or not file.is_file():
            self.svt_av1_warning_message.setText("<b>Status:</b> No file selected")
        elif not svt_av1_version(self.main.svt_av1):
            self.svt_av1_warning_message.setText("<b>Status:</b> Not a SVT AV1 executable")
        else:
            self.svt_av1_warning_message.setText("<b>Status:</b> SVT AV1 executable identified")

    def check_ffmpeg_dir(self, directory):
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
            self.ffmpeg_file_info.setText("<br>".join(warnings))
        else:
            self.ffmpeg_file_info.setText("Binary files found!")

    def open_binary_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self)
        if not directory:
            self.path_radio.setChecked(True)
            self.ffmpeg_select.setDisabled(True)
        self.ffmpeg_file_path.setText(str(directory))
        self.check_ffmpeg_dir(directory)
        self.ffmpeg_check()

    def open_svt_av1_binary(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption="Select SVTAV1 Executable",
                                                         filter="Executable (*.exe)")
        if not filename or not filename[0]:
            self.svt_av1_binary_radio.setChecked(True)
            self.svt_av1_select.setDisabled(True)
        self.svt_av1_file_path.setText(str(filename[0]))
        self.main.svt_av1 = filename[0]
        self.check_svt_av1()

    def ffmpeg_check(self):
        if self.main.ffmpeg_version and self.main.ffprobe_version:
            ff_config = Flix(ffmpeg=self.main.ffmpeg).ffmpeg_configuration()
            self.ffmpeg_warning_message.setText("<b>Status:</b> Everything is under control. Situation normal.")
            self.main.enable_converters()
            # if 'libaom' not in ff_config:
            #     self.main.disable_converters('x265')
            if 'libx265' not in ff_config:
                self.ffmpeg_warning_message.setText("<b>Status:</b> "
                                                    "libx265 support not found, disabled x265 conversion.")
                self.main.disable_converters('x265')
        elif self.main.ffmpeg_version:
            self.ffmpeg_warning_message.setText("<b>Status:</b> ffprobe not found")
            self.main.disable_converters()
        elif self.main.ffprobe_version:
            self.ffmpeg_warning_message.setText("<b>Status:</b> ffmpeg not found")
            self.main.disable_converters()
        else:
            self.ffmpeg_warning_message.setText("<b>Status:</b> ffmpeg and ffprobe not found")
            self.main.disable_converters()
        self.main.default_status()
        if self.main.ffmpeg_version:
            logger.debug(f"ffmpeg version: {self.main.ffmpeg_version}")
        if self.main.ffprobe_version:
            logger.debug(f"ffprobe version: {self.main.ffprobe_version}")
