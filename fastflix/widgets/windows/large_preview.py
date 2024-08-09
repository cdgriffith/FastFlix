# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional, TYPE_CHECKING
import secrets

from PySide6 import QtWidgets, QtCore, QtGui

from fastflix.flix import (
    generate_thumbnail_command,
)
from fastflix.encoders.common import helpers
from fastflix.resources import get_icon
from fastflix.language import t

if TYPE_CHECKING:
    from fastflix.widgets.main import Main

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
    def __init__(self, parent: "Main"):
        super().__init__()
        self.main = parent
        self.label = ImageLabel(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        screen = self.main.app.primaryScreen()
        size = screen.size()
        self.setMaximumWidth(size.width())
        self.setMaximumHeight(size.height())
        self.setMinimumSize(400, 400)
        self.current_image = QtGui.QPixmap(get_icon("onyx-cover", self.main.app.fastflix.config.theme))
        self.last_path: Optional[Path] = None
        self.last_command = "NOPE"
        self.setWindowTitle(t("Preview - Press Q to Exit"))

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key_Q:
            self.hide()
        super(LargePreview, self).keyPressEvent(a0)

    def generate_image(self):
        settings = self.main.app.fastflix.current_video.video_settings.model_dump()
        if not self.main.app.fastflix.current_video.video_settings.video_encoder_settings:
            return

        if (
            self.main.app.fastflix.current_video.video_settings.video_encoder_settings.pix_fmt == "yuv420p10le"
            and self.main.app.fastflix.current_video.color_space.startswith("bt2020")
        ):
            settings["remove_hdr"] = True

        filters = helpers.generate_filters(
            enable_opencl=self.main.app.fastflix.opencl_support,
            start_filters="select=eq(pict_type\\,I)" if self.main.widgets.thumb_key.isChecked() else None,
            scale=self.main.app.fastflix.current_video.scale,
            **settings,
        )

        output = self.main.app.fastflix.config.work_path / f"large_preview_{secrets.token_hex(16)}.tiff"

        thumb_command = generate_thumbnail_command(
            config=self.main.app.fastflix.config,
            source=self.main.source_material,
            output=output,
            filters=filters,
            start_time=self.main.preview_place,
            enable_opencl=self.main.app.fastflix.opencl_support,
            input_track=self.main.app.fastflix.current_video.video_settings.selected_track,
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
