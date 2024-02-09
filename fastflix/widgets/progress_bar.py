# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass, field
from typing import Callable

import reusables
from PySide6 import QtCore, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp

logger = logging.getLogger("fastflix")


@dataclass
class Task:
    name: str
    command: Callable
    kwargs: dict = field(default_factory=dict)


class ProgressBar(QtWidgets.QFrame):
    progress_signal = QtCore.Signal(int)
    stop_signal = QtCore.Signal()

    def __init__(
        self,
        app: FastFlixApp,
        tasks: list[Task],
        signal_task: bool = False,
        auto_run: bool = True,
        can_cancel: bool = False,
        hidden: bool = False,
    ):
        super().__init__(None)
        self.app = app

        self.tasks = tasks
        self.signal_task = signal_task
        self.cancelled = False

        self.setObjectName("ProgressBar")
        self.setStyleSheet("#ProgressBar{border: 1px solid #aaa}")

        self.setMinimumWidth(400)
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.status = QtWidgets.QLabel()
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 500, 75)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.progress_bar)
        if can_cancel:
            cancel_button = QtWidgets.QPushButton(t("Cancel"))
            cancel_button.clicked.connect(self.cancel)
            self.layout.addWidget(cancel_button)
        self.setLayout(self.layout)

        if not hidden:
            self.show()
        if auto_run:
            self.run()

    def cancel(self):
        if self.signal_task:
            self.stop_signal.emit()
        else:
            self.cancelled = True
        self.close()

    @reusables.log_exception("fastflix")
    def run(self):
        if not self.tasks:
            logger.error("Progress bar RUN called without any tasks")
            return
        ratio = 100 / len(self.tasks)
        self.progress_bar.setValue(0)

        if self.signal_task:
            self.status.setText(self.tasks[0].name)
            self.progress_signal.connect(self.update_progress)
            self.tasks[0].kwargs["signal"] = self.progress_signal
            self.tasks[0].kwargs["stop_signal"] = self.stop_signal
            self.tasks[0].command(config=self.app.fastflix.config, app=self.app, **self.tasks[0].kwargs)

        else:
            for i, task in enumerate(self.tasks, start=1):
                logger.info(f"Running task {task.name}")
                self.status.setText(task.name)
                self.app.processEvents()
                if self.app.fastflix.shutting_down:
                    self.close()
                try:
                    task.command(config=self.app.fastflix.config, app=self.app, **task.kwargs)
                except Exception:
                    logger.exception(f"Could not run task {task.name} with config {self.app.fastflix.config}")
                    self.close()
                    raise
                self.progress_bar.setValue(int(i * ratio))
                if self.cancelled:
                    return

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.app.processEvents()
        if self.app.fastflix.shutting_down:
            self.stop_signal.emit()
            self.close()
