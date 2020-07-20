#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from subprocess import Popen, PIPE, run, STDOUT

import reusables

from fastflix.shared import QtCore

logger = logging.getLogger("fastflix")

__all__ = ["Worker"]


class Worker(QtCore.QThread):
    def __init__(self, app, command="", target=None, params=None, cmd_type="convert"):
        super(Worker, self).__init__(app)
        self.app = app
        self.command = command
        self.target = target
        self.params = params if params else {}
        self.cmd_type = cmd_type
        self.process = None
        self.killed = False

    def run(self):
        if self.command:
            logger.info(f"Running command: {self.command}")
            self.process = self.start_exec()
            while True:
                next_line = self.process.stdout.readline().decode("utf-8")
                if not next_line:
                    if self.process.poll() is not None:
                        break
                    else:
                        continue
                logger.debug(f"ffmpeg - {next_line}")
            return_code = self.process.poll()
            if self.killed:
                return self.app.cancelled.emit()
        else:
            try:
                return_code = self.target(**self.params)
            except Exception as err:
                logger.error(f"Could not run target {self.target}: {err}")
                return self.app.completed.emit(1)

        if self.cmd_type == "convert":
            self.app.completed.emit(return_code)
        elif self.cmd_type == "thumb":
            self.app.thumbnail_complete.emit()

    def start_exec(self):
        return Popen(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)

    def is_alive(self):
        if not self.process:
            return False
        return True if self.process.poll() is None else False

    def kill(self):
        if self.process and self.is_alive():
            self.killed = True
            if reusables.win_based:
                run(f"TASKKILL /F /PID {self.process.pid} /T", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            else:
                run(f"kill -9 {self.process.pid}", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            return self.process.terminate()

    def __del__(self):
        self.kill()
