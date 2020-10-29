# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pkg_resources
import time
from collections import namedtuple
from typing import List

from qtpy import QtWidgets, QtGui, QtCore

from fastflix.models.config import Config

Task = namedtuple("Task", ["name", "command", "kwargs"])


class ProgressBar(QtWidgets.QWidget):
    progress_signal = QtCore.Signal(int)

    def __init__(self, app: QtWidgets.QApplication, config: Config, tasks: List[Task], signal_task=False):
        super().__init__(None)
        self.status = QtWidgets.QLabel()
        self.setMinimumWidth(400)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 500, 75)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)
        # self.setGeometry(300, 300, 550, 100)
        self.show()
        ratio = 100 // len(tasks)
        self.progress_bar.setValue(0)

        if signal_task:
            self.status.setText(tasks[0].name)
            self.progress_signal.connect(self.update_progress)
            tasks[0].kwargs["signal"] = self.progress_signal
            tasks[0].command(config=config, app=app, **tasks[0].kwargs)
        else:
            for i, task in enumerate(tasks, start=1):
                self.status.setText(task.name)
                task.command(config=config, app=app, **task.kwargs)
                self.progress_bar.setValue(int(i * ratio))

    def update_progress(self, value):
        self.progress_bar.setValue(value)
