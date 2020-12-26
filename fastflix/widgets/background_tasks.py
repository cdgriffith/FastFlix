#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from subprocess import PIPE, STDOUT, run

from qtpy import QtCore

from fastflix.language import t

logger = logging.getLogger("fastflix")

__all__ = ["ThumbnailCreator"]


class ThumbnailCreator(QtCore.QThread):
    def __init__(self, app, command=""):
        super().__init__(app)
        self.app = app
        self.command = command

    def run(self):
        logger.debug(f"{t('Generating thumbnail')}: {self.command}")
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
                logger.error(f"{t('Could not generate thumbnail')}: {result.stdout}")
            self.app.thumbnail_complete.emit(0)
        else:
            self.app.thumbnail_complete.emit(1)
        self.exit(0)


class SubtitleFix(QtCore.QThread):
    def __init__(self, app, mkv_prop_edit, video_path):
        super().__init__(app)
        self.app = app
        self.mkv_prop_edit = mkv_prop_edit
        self.video_path = video_path

    def run(self):
        output_file = str(self.video_path).replace("\\", "/")
        logger.info(t("Will fix first subtitle track to not be default"))
        try:
            result = run(
                [self.mkv_prop_edit, output_file, "--edit", "track:s1", "--set", "flag-default=0"],
                stdout=PIPE,
                stderr=STDOUT,
            )
        except Exception:
            logger.exception(t("Could not fix first subtitle track"))
        else:
            if result.returncode != 0:
                logger.warning(f'{t("Could not fix first subtitle track")}: {result.stdout}')
