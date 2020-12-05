#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from subprocess import PIPE, STDOUT, run

import reusables
from qtpy import QtCore, QtGui, QtWidgets

logger = logging.getLogger("fastflix")

__all__ = ["ThumbnailCreator"]


class ThumbnailCreator(QtCore.QThread):
    def __init__(self, app, command=""):
        super().__init__(app)
        self.app = app
        self.command = command

    def run(self):
        logger.debug(f"Generating thumbnail: {self.command}")
        result = run(self.command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)
        if result.returncode > 0:
            if "No such filter: 'zscale'" in result.stdout.decode(encoding="utf-8", errors="ignore"):
                logger.error(
                    "Could not generate thumbnail because you are using an outdated FFmpeg! "
                    "Please use FFmpeg 4.3+ built against the latest zimg libraries. "
                    "Static builds available at https://ffmpeg.org/download.html "
                    "(Linux distributions are often slow to update)"
                )
            else:
                logger.error(f"Could not generate thumbnail: {result.stdout}")
            self.app.thumbnail_complete.emit(0)
        else:
            self.app.thumbnail_complete.emit(1)
        self.exit(0)
