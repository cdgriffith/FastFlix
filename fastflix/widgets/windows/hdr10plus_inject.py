# -*- coding: utf-8 -*-
from pathlib import Path
import os
import logging
import secrets
from subprocess import run, PIPE

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QAbstractItemView

from fastflix.language import t
from fastflix.flix import probe
from fastflix.shared import yes_no_message, error_message
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.resources import group_box_style, get_icon

logger = logging.getLogger("fastflix")


class HDR10PlusInjectWindow(QtWidgets.QWidget):
    def __init__(self, app, main, items=None):
        super().__init__(None)
        self.app = app
        self.main = main
        self.selected_stream = None

        self.movie_file = QtWidgets.QLineEdit()
        self.movie_file.setEnabled(False)
        self.movie_file.setFixedWidth(400)
        self.movie_file_button = QtWidgets.QPushButton(
            icon=QtGui.QIcon(get_icon("onyx-output", self.app.fastflix.config.theme))
        )
        self.movie_file_button.clicked.connect(self.movie_open)

        self.hdr10p_file = QtWidgets.QLineEdit()
        self.hdr10p_file.setEnabled(False)
        self.hdr10p_file_button = QtWidgets.QPushButton(
            icon=QtGui.QIcon(get_icon("onyx-output", self.app.fastflix.config.theme))
        )
        self.hdr10p_file_button.clicked.connect(self.hdr10p_open)

        self.output_file = QtWidgets.QLineEdit()
        self.output_file.setFixedWidth(400)
        self.output_file_button = QtWidgets.QPushButton(
            icon=QtGui.QIcon(get_icon("onyx-output", self.app.fastflix.config.theme))
        )
        self.output_file_button.clicked.connect(self.set_output_file)
        self.output_file.textChanged.connect(self.prep_command)

        line_1 = QtWidgets.QHBoxLayout()
        line_1.addWidget(QtWidgets.QLabel("Movie File"))
        line_1.addWidget(self.movie_file)
        line_1.addWidget(self.movie_file_button)

        line_3 = QtWidgets.QHBoxLayout()
        line_3.addWidget(QtWidgets.QLabel("HDR10+ File"))
        line_3.addWidget(self.hdr10p_file)
        line_3.addWidget(self.hdr10p_file_button)

        self.info_bubble = QtWidgets.QLabel("")
        self.command_bubble = QtWidgets.QLineEdit("")
        self.command_bubble.setFixedWidth(400)
        # self.command_bubble.setWordWrap(True)
        # self.command_bubble.setFixedHeight(400)

        layout = QtWidgets.QVBoxLayout()

        output_lin = QtWidgets.QHBoxLayout()
        output_lin.addWidget(QtWidgets.QLabel("Output File"))
        output_lin.addWidget(self.output_file)
        output_lin.addWidget(self.output_file_button)

        bottom_line = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.clicked.connect(self.hide)
        bottom_line.addWidget(cancel)
        start = QtWidgets.QPushButton("Start")
        start.clicked.connect(self.start)
        bottom_line.addWidget(start)

        layout.addLayout(line_1)
        layout.addWidget(self.info_bubble)
        layout.addLayout(line_3)
        layout.addLayout(output_lin)
        layout.addWidget(self.command_bubble)
        layout.addLayout(bottom_line)
        self.setLayout(layout)

    def movie_open(self):
        self.selected_stream = None
        self.movie_file.setText("")
        movie_name = QtWidgets.QFileDialog.getOpenFileName(self)
        if not movie_name or not movie_name[0]:
            return
        try:
            results = probe(self.app, movie_name[0])
        except Exception as err:
            error_message(f"Invalid file: {err}")
            return
        for result in results["streams"]:
            if result["codec_type"] == "video":
                if result["codec_name"] == "hevc":
                    self.selected_stream = result
                    break
        if not self.selected_stream:
            error_message("No HEVC video stream found")
            return
        self.info_bubble.setText(f"Selected stream index: {self.selected_stream['index']}")
        self.movie_file.setText(movie_name[0])
        self.prep_command()

    def hdr10p_open(self):
        hdr10p_file = QtWidgets.QFileDialog.getOpenFileName(self)
        if not hdr10p_file or not hdr10p_file[0]:
            return
        self.hdr10p_file.setText(hdr10p_file[0])
        self.prep_command()

    def set_output_file(self):
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption="Save Video As",
            # dir=str(Path(*self.generate_output_filename)) + f"{self.widgets.output_type_combo.currentText()}",
            # filter=f"Save File (*.{extension})",
        )
        if filename and filename[0]:
            self.output_file.setText(filename[0])
        self.prep_command()

    def prep_command(self):
        print("called prep")
        if not self.movie_file.text() or not self.hdr10p_file.text() or not self.output_file.text():
            print("Nope", "1", self.movie_file.text(), "2", self.hdr10p_file.text(), "3", self.output_file.text())
            return

        command = (
            f'{self.app.fastflix.config.ffmpeg} -loglevel panic -i "{self.movie_file.text()}" '
            f'-map 0:{self.selected_stream["index"]} -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | '
            f"{self.app.fastflix.config.hdr10plus_parser} inject -i - -j {self.hdr10p_file.text()} -o - | "
            f'{self.app.fastflix.config.ffmpeg} -loglevel panic -i - -i {self.movie_file.text()} -map 0:0 -c:0 copy -map 1:a -map 1:s -map 1:d -c:1 copy "{self.output_file.text()}"'
        )

        print(command)
        self.command_bubble.setText(command)

    def start(self):
        run(self.command_bubble.text(), shell=True)
        error_message("Done")
