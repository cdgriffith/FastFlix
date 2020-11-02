# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Callable, Dict, List

import reusables
from qtpy import QtCore, QtWidgets


@dataclass
class Task:
    name: str
    command: Callable
    kwargs: Dict = field(default_factory=dict)


class ProgressBar(QtWidgets.QWidget):
    progress_signal = QtCore.Signal(int)

    def __init__(
        self,
        app: QtWidgets.QApplication,
        tasks: List[Task],
        signal_task: bool = False,
        auto_run: bool = True,
    ):
        super().__init__(None)
        self.app = app
        self.tasks = tasks
        self.signal_task = signal_task

        self.setMinimumWidth(400)
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)

        self.status = QtWidgets.QLabel()
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 500, 75)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

        self.show()
        if auto_run:
            self.run()

    @reusables.log_exception("fastflix")
    def run(self):
        ratio = 100 // len(self.tasks)
        self.progress_bar.setValue(0)

        if self.signal_task:
            self.status.setText(self.tasks[0].name)
            self.progress_signal.connect(self.update_progress)
            self.tasks[0].kwargs["signal"] = self.progress_signal
            self.tasks[0].command(config=self.app.fastflix.config, app=self.app, **self.tasks[0].kwargs)
        else:
            for i, task in enumerate(self.tasks, start=1):
                self.status.setText(task.name)
                self.app.processEvents()
                task.command(config=self.app.fastflix.config, app=self.app, **task.kwargs)
                self.progress_bar.setValue(int(i * ratio))

    def update_progress(self, value):
        self.progress_bar.setValue(value)
