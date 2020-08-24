#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from subprocess import PIPE, run, STDOUT

import reusables

from qtpy import QtWidgets, QtCore, QtGui

logger = logging.getLogger("fastflix")

__all__ = ["ThumbnailCreator"]


class ThumbnailCreator(QtCore.QThread):
    def __init__(self, app, command=""):
        super(ThumbnailCreator, self).__init__(app)
        self.app = app
        self.command = command

    def run(self):
        logger.debug(f"Generating thumbnail: {self.command}")
        result = run(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)
        if result.returncode > 0:
            logger.error(f"Could not generate thumbnail: {result.stdout}")
        else:
            self.app.thumbnail_complete.emit()
