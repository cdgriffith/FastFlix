#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from typing import List, Tuple, Union

from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import AttachmentTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import VideoSettings
from fastflix.shared import link

logger = logging.getLogger("fastflix")


class CoverPanel(QtWidgets.QWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()

        layout = QtWidgets.QGridLayout()

        sp = QtWidgets.QSizePolicy()
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)

        # row, column, row span, column span
        layout.addWidget(QtWidgets.QLabel(t("Poster Cover")), 0, 0, 1, 5)
        layout.addWidget(QtWidgets.QLabel(t("Landscape Cover")), 0, 6, 1, 4)
        info_label = QtWidgets.QLabel(
            link(
                "https://codecalamity.com/guides/video-thumbnails/",
                t("Enabling cover thumbnails on your system"),
                app.fastflix.config.theme,
            )
        )
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label, 10, 0, 1, 9, QtCore.Qt.AlignLeft)

        poster_options_layout = QtWidgets.QHBoxLayout()
        self.cover_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Cover"))
        self.small_cover_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Small Cover (no preview)"))

        poster_options_layout.addWidget(self.cover_passthrough_checkbox)
        poster_options_layout.addWidget(self.small_cover_passthrough_checkbox)

        land_options_layout = QtWidgets.QHBoxLayout()
        self.cover_land_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Landscape Cover"))
        self.small_cover_land_passthrough_checkbox = QtWidgets.QCheckBox(t("Copy Small Landscape Cover  (no preview)"))

        land_options_layout.addWidget(self.cover_land_passthrough_checkbox)
        land_options_layout.addWidget(self.small_cover_land_passthrough_checkbox)

        self.cover_passthrough_checkbox.toggled.connect(lambda: self.cover_passthrough_check())
        self.small_cover_passthrough_checkbox.toggled.connect(lambda: self.small_cover_passthrough_check())
        self.cover_land_passthrough_checkbox.toggled.connect(lambda: self.cover_land_passthrough_check())
        self.small_cover_land_passthrough_checkbox.toggled.connect(lambda: self.small_cover_land_passthrough_check())

        self.poster = QtWidgets.QLabel()
        self.poster.setSizePolicy(sp)

        self.landscape = QtWidgets.QLabel()
        self.landscape.setSizePolicy(sp)

        layout.addLayout(poster_options_layout, 1, 0, 1, 4)
        layout.addLayout(land_options_layout, 1, 6, 1, 4)

        layout.addWidget(self.poster, 2, 0, 8, 4)
        layout.addWidget(self.landscape, 2, 6, 8, 4)

        layout.addLayout(self.init_cover(), 9, 0, 1, 4)
        layout.addLayout(self.init_landscape_cover(), 9, 6, 1, 4)
        layout.columnStretch(5)

        self.setLayout(layout)

    def init_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.cover_path = QtWidgets.QLineEdit()
        self.cover_path.textChanged.connect(lambda: self.update_cover())
        self.cover_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        )
        self.cover_button.clicked.connect(lambda: self.select_cover())

        layout.addWidget(self.cover_path)
        layout.addWidget(self.cover_button)
        return layout

    def select_cover(self):
        dirname = Path(self.cover_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption=t("Cover"),
            dir=str(dirname),
            filter=f"{t('Supported Image Files')} (*.png *.jpeg *.jpg)",
        )
        if not filename or not filename[0]:
            return
        self.cover_path.setText(filename[0])
        self.update_cover()

    def update_cover(self, cover_path=None):
        if cover_path:
            cover = str(cover_path)
        else:
            cover = self.cover_path.text().strip()
        if not cover:
            self.poster.setPixmap(QtGui.QPixmap())
            self.update_cover_settings()
            self.main.page_update(build_thumbnail=False)
            return
        if (
            not Path(cover).exists()
            or not Path(cover).is_file()
            or not cover.lower().endswith((".jpg", ".png", ".jpeg"))
        ):
            return
        try:
            pixmap = QtGui.QPixmap(cover)
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.poster.setPixmap(pixmap)
        except Exception:
            logger.exception(t("Bad image"))
            self.cover_path.setText("")
        else:
            self.update_cover_settings()
            self.main.page_update(build_thumbnail=False)

    def init_landscape_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.cover_land_path = QtWidgets.QLineEdit()
        self.cover_land_path.textChanged.connect(lambda: self.update_landscape_cover())
        self.landscape_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        )
        self.landscape_button.clicked.connect(lambda: self.select_landscape_cover())

        layout.addWidget(self.cover_land_path)
        layout.addWidget(self.landscape_button)
        return layout

    def select_landscape_cover(self):
        dirname = Path(self.cover_land_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption=t("Landscape Cover"),
            dir=str(dirname),
            filter=f"{t('Supported Image Files')} (*.png *.jpeg *.jpg)",
        )
        if not filename or not filename[0]:
            return
        self.cover_land_path.setText(filename[0])
        self.update_landscape_cover()

    def update_landscape_cover(self, cover_path=None):
        if cover_path:
            cover = str(cover_path)
        else:
            cover = self.cover_land_path.text().strip()
        if not cover:
            self.landscape.setPixmap(QtGui.QPixmap())
            self.update_cover_settings()
            self.main.page_update(build_thumbnail=False)
            return

        if (
            not Path(cover).exists()
            or not Path(cover).is_file()
            or not cover.lower().endswith((".jpg", ".png", ".jpeg"))
        ):
            return
        try:
            pixmap = QtGui.QPixmap(cover)
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.landscape.setPixmap(pixmap)
        except Exception:
            logger.exception(t("Bad image"))
            self.cover_land_path.setText("")
        else:
            self.update_cover_settings()
            self.main.page_update(build_thumbnail=False)

    def get_attachment(self, filename) -> Tuple[Union[Path, None], Union[int, None]]:
        attr = getattr(self, f"{filename}_path", None)
        cover_image = None
        index = None
        if attr and attr.text().strip():
            cover_image = Path(attr.text().strip())
        if (
            self.app.fastflix.current_video
            and getattr(self, f"{filename}_passthrough_checkbox").isChecked()
            and filename in self.attachments
        ):
            cover_image = self.app.fastflix.current_video.work_path / self.attachments[filename].name
            index = self.attachments[filename].stream
        return cover_image if cover_image else None, index

    def update_cover_settings(self):
        if not self.app.fastflix.current_video:
            return
        start_outdex = (
            1  # Video Track
            + len(self.app.fastflix.current_video.audio_tracks)
            + len(self.app.fastflix.current_video.subtitle_tracks)
        )
        attachments: list[AttachmentTrack] = []

        for filename in ("cover", "cover_land", "small_cover", "small_cover_land"):
            attachment, index = self.get_attachment(filename)
            if attachment:
                attachments.append(
                    AttachmentTrack(
                        index=index,
                        outdex=start_outdex,
                        file_path=attachment,
                        filename=filename,
                        attachment_type="cover",
                    )
                )
                start_outdex += 1
        self.app.fastflix.current_video.attachment_tracks = attachments

    def cover_passthrough_check(self):
        checked = self.cover_passthrough_checkbox.isChecked()
        if checked and "cover" in self.attachments:
            self.cover_path.setDisabled(True)
            self.cover_button.setDisabled(True)
            pixmap = QtGui.QPixmap(str(self.app.fastflix.current_video.work_path / self.attachments.cover.name))
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.poster.setPixmap(pixmap)
        else:
            self.cover_path.setDisabled(False)
            self.cover_button.setDisabled(False)
            if not self.cover_path.text() or not Path(self.cover_path.text()).exists():
                self.poster.setPixmap(QtGui.QPixmap())
            else:
                pixmap = QtGui.QPixmap(self.cover_path.text())
                pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
                self.poster.setPixmap(pixmap)

        self.main.page_update(build_thumbnail=False)

    def small_cover_passthrough_check(self):
        self.main.page_update(build_thumbnail=False)

    def cover_land_passthrough_check(self):
        checked = self.cover_land_passthrough_checkbox.isChecked()
        if checked and "cover_land" in self.attachments:
            self.cover_land_path.setDisabled(True)
            self.landscape_button.setDisabled(True)
            pixmap = QtGui.QPixmap(str(self.app.fastflix.current_video.work_path / self.attachments.cover_land.name))
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.landscape.setPixmap(pixmap)
        else:
            self.cover_land_path.setDisabled(False)
            self.landscape_button.setDisabled(False)
            if not self.cover_land_path.text() or not Path(self.cover_land_path.text()).exists():
                self.landscape.setPixmap(QtGui.QPixmap())
            else:
                pixmap = QtGui.QPixmap(self.cover_land_path.text())
                pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
                self.landscape.setPixmap(pixmap)

        self.main.page_update(build_thumbnail=False)

    def small_cover_land_passthrough_check(self):
        self.main.page_update(build_thumbnail=False)

    def clear_covers(self, reconnect=True):
        self.cover_passthrough_checkbox.toggled.disconnect()
        self.small_cover_passthrough_checkbox.toggled.disconnect()
        self.cover_land_passthrough_checkbox.toggled.disconnect()
        self.small_cover_land_passthrough_checkbox.toggled.disconnect()

        self.cover_passthrough_checkbox.setChecked(False)
        self.small_cover_passthrough_checkbox.setChecked(False)
        self.cover_land_passthrough_checkbox.setChecked(False)
        self.small_cover_land_passthrough_checkbox.setChecked(False)

        self.cover_passthrough_checkbox.setDisabled(True)
        self.small_cover_passthrough_checkbox.setDisabled(True)
        self.cover_land_passthrough_checkbox.setDisabled(True)
        self.small_cover_land_passthrough_checkbox.setDisabled(True)
        self.attachments = Box()

        self.poster.setPixmap(QtGui.QPixmap())
        self.landscape.setPixmap(QtGui.QPixmap())

        self.cover_path.setDisabled(False)
        self.cover_path.setText("")
        self.cover_button.setDisabled(False)
        self.cover_land_path.setDisabled(False)
        self.cover_land_path.setText("")
        self.landscape_button.setDisabled(False)

        if reconnect:
            self.cover_passthrough_checkbox.toggled.connect(lambda: self.cover_passthrough_check())
            self.small_cover_passthrough_checkbox.toggled.connect(lambda: self.small_cover_passthrough_check())
            self.cover_land_passthrough_checkbox.toggled.connect(lambda: self.cover_land_passthrough_check())
            self.small_cover_land_passthrough_checkbox.toggled.connect(
                lambda: self.small_cover_land_passthrough_check()
            )

    def new_source(self, attachments):
        self.clear_covers(reconnect=False)

        for attachment in attachments:
            filename = attachment.get("tags", {}).get("filename", "")
            base_name = filename.rsplit(".", 1)[0]
            file_path = self.app.fastflix.current_video.work_path / filename
            if base_name == "cover" and file_path.exists():
                self.cover_passthrough_checkbox.setChecked(True)
                self.cover_passthrough_checkbox.setDisabled(False)
                self.update_cover(str(file_path))
                self.cover_path.setDisabled(True)
                self.cover_path.setText("")
                self.cover_button.setDisabled(True)
                self.attachments.cover = {"name": filename, "stream": attachment.index, "tags": attachment.tags}
            if base_name == "cover_land" and file_path.exists():
                self.cover_land_passthrough_checkbox.setChecked(True)
                self.cover_land_passthrough_checkbox.setDisabled(False)
                self.update_landscape_cover(str(file_path))
                self.cover_land_path.setDisabled(True)
                self.cover_land_path.setText("")
                self.landscape_button.setDisabled(True)
                self.attachments.cover_land = {"name": filename, "stream": attachment.index, "tags": attachment.tags}
            if base_name == "small_cover" and file_path.exists():
                self.small_cover_passthrough_checkbox.setChecked(True)
                self.small_cover_passthrough_checkbox.setDisabled(False)
                self.attachments.small_cover = {"name": filename, "stream": attachment.index, "tags": attachment.tags}
            if base_name == "small_cover_land" and file_path.exists():
                self.small_cover_land_passthrough_checkbox.setChecked(True)
                self.small_cover_land_passthrough_checkbox.setDisabled(False)
                self.attachments.small_cover_land = {
                    "name": filename,
                    "stream": attachment.index,
                    "tags": attachment.tags,
                }

        self.cover_passthrough_checkbox.toggled.connect(lambda: self.cover_passthrough_check())
        self.small_cover_passthrough_checkbox.toggled.connect(lambda: self.small_cover_passthrough_check())
        self.cover_land_passthrough_checkbox.toggled.connect(lambda: self.cover_land_passthrough_check())
        self.small_cover_land_passthrough_checkbox.toggled.connect(lambda: self.small_cover_land_passthrough_check())

    def reload_from_queue(self, streams, attachment_tracks):
        self.new_source(streams.attachment)
        self.cover_passthrough_checkbox.setChecked(False)
        self.cover_land_passthrough_checkbox.setChecked(False)
        self.small_cover_land_passthrough_checkbox.setChecked(False)
        self.small_cover_passthrough_checkbox.setChecked(False)

        for attachment in attachment_tracks:
            if attachment.filename == "cover":
                if attachment.index is None:
                    self.cover_path.setText(str(attachment.file_path))
                    self.update_cover(attachment.file_path)
                else:
                    self.cover_passthrough_checkbox.setChecked(True)
            if attachment.filename == "cover_land":
                if attachment.index is None:
                    self.cover_land_path.setText(str(attachment.file_path))
                    self.update_landscape_cover(attachment.file_path)
                else:
                    self.cover_land_passthrough_checkbox.setChecked(True)
            if attachment.filename == "small_cover_land":
                if attachment.index is not None:
                    self.small_cover_land_passthrough_checkbox.setChecked(True)
            if attachment.filename == "small_cover":
                if attachment.index is not None:
                    self.small_cover_passthrough_checkbox.setChecked(True)


#     def update_cover_settings(self):
#         start_outdex = (
#             1  # Video Track
#             + len(self.app.fastflix.current_video.audio_tracks)
#             + len(self.app.fastflix.current_video.subtitle_tracks)
#         )
#         attachments: list[AttachmentTrack] = []
#
#         for filename in ("cover", "cover_land", "small_cover", "small_cover_land"):
#             attachment = self.get_attachment(filename)
#             if attachment:
#                 attachments.append(
#                     AttachmentTrack(
#                         outdex=start_outdex, file_path=attachment, filename=filename, attachment_type="cover"
#                     )
#                 )
#                 start_outdex += 1
#         self.app.fastflix.current_video.video_settings.attachment_tracks = attachments
