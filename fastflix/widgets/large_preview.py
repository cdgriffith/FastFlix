# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional
import secrets

from qtpy import QtWidgets, QtCore, QtGui

from fastflix.flix import (
    generate_thumbnail_command,
)
from fastflix.encoders.common import helpers
from fastflix.resources import photo_icon

__all__ = ["LargePreview"]

logger = logging.getLogger("fastflix")

class ImageLabel(QtWidgets.QLabel):
    
    def __init__(self, parent):
        super(ImageLabel, self).__init__(parent)
        self.lp = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAlignment(QtCore.Qt.AlignHCenter)
        
    def resizeEvent(self, QResizeEvent):
        self.resize(self.lp.width(), self.lp.height())
        self.setPixmap(self.lp.current_image.scaled(self.lp.width(), self.lp.height(), QtCore.Qt.KeepAspectRatio))
        super(ImageLabel, self).resizeEvent(QResizeEvent)


class LargePreview(QtWidgets.QWidget):

    def __init__(self, parent):
        super().__init__()
        self.main = parent
        self.label = ImageLabel(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        screen = self.main.app.primaryScreen()
        size = screen.size()
        self.setMaximumWidth(size.width())
        self.setMaximumHeight(size.height())
        self.setMinimumSize(400, 400)
        self.current_image = QtGui.QPixmap(photo_icon)
        self.last_path: Optional[Path] = None
        self.last_command = "NOPE"

    def generate_image(self):
        settings = self.main.app.fastflix.current_video.video_settings.dict()

        if (
                self.main.app.fastflix.current_video.video_settings.video_encoder_settings.pix_fmt == "yuv420p10le"
                and self.main.app.fastflix.current_video.color_space.startswith("bt2020")
        ):
            settings["remove_hdr"] = True

        filters = helpers.generate_filters(
            start_filters="select=eq(pict_type\\,I)" if self.main.widgets.thumb_key.isChecked() else None,
            **settings,
        )

        output = self.main.app.fastflix.config.work_path / f"large_preview_{secrets.token_hex(16)}.tiff"

        thumb_command = generate_thumbnail_command(
            config=self.main.app.fastflix.config,
            source=self.main.input_video,
            output=output,
            filters=filters,
            start_time=self.main.preview_place,
            input_track=self.main.app.fastflix.current_video.video_settings.selected_track
        )
        if thumb_command == self.last_command:
            return

        logger.info(f"Generating large thumbnail: {thumb_command}")

        thumb_run = run(thumb_command, shell=True, stderr=PIPE, stdout=PIPE)
        if thumb_run.returncode > 0:
            logger.warning(f"Could not generate large thumbnail: {thumb_run.stdout} |----| {thumb_run.stderr}")
            return

        self.current_image = QtGui.QPixmap(str(output))
        if self.last_path:
            try:
                self.last_path.unlink(missing_ok=True)
            except OSError:
                logger.warning(f"Could not delete last large preview {self.last_path}")
        self.last_path = output
        self.label.setPixmap(self.current_image)
        self.resize(self.current_image.width(), self.current_image.height())

    def resizeEvent(self, QResizeEvent):
        self.label.resizeEvent(QResizeEvent)
        super(LargePreview, self).resizeEvent(QResizeEvent)
