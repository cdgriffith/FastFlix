#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path

from box import Box
from qtpy import QtCore, QtGui, QtWidgets

logger = logging.getLogger("fastflix")


class CoverPanel(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent.main
        self.attachments = Box()

        layout = QtWidgets.QGridLayout()

        sp = QtWidgets.QSizePolicy()
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)

        # row, column, row span, column span
        layout.addWidget(QtWidgets.QLabel("Poster Cover"), 0, 0, 1, 5)
        layout.addWidget(QtWidgets.QLabel("Landscape Cover"), 0, 6, 1, 4)
        info_label = QtWidgets.QLabel(
            "<a href='https://codecalamity.com/guides/video-thumbnails/'>"
            "Enabling cover thumbnails on your system</a>"
        )
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label, 10, 0, 1, 9, QtCore.Qt.AlignLeft)

        poster_options_layout = QtWidgets.QHBoxLayout()
        self.cover_passthrough_checkbox = QtWidgets.QCheckBox("Copy Cover")
        self.small_cover_passthrough_checkbox = QtWidgets.QCheckBox("Copy Small Cover (no preview)")

        poster_options_layout.addWidget(self.cover_passthrough_checkbox)
        poster_options_layout.addWidget(self.small_cover_passthrough_checkbox)

        land_options_layout = QtWidgets.QHBoxLayout()
        self.cover_land_passthrough_checkbox = QtWidgets.QCheckBox("Copy Landscape Cover")
        self.small_cover_land_passthrough_checkbox = QtWidgets.QCheckBox("Copy Small Landscape Cover  (no preview)")

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
            self, caption="cover", directory=str(dirname), filter="Supported Image Files (*.png;*.jpeg;*.jpg)"
        )
        if not filename or not filename[0]:
            return
        self.cover_path.setText(filename[0])
        self.update_cover()

    def update_cover(self, cover_path=None):
        if cover_path:
            cover = cover_path
        else:
            cover = self.cover_path.text().strip()
        if not cover:
            self.poster.setPixmap(QtGui.QPixmap())
            self.main.page_update()
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
            logger.exception("Bad image")
            self.cover_path.setText("")
        else:
            self.main.page_update()

    def init_landscape_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.cover_land = QtWidgets.QLineEdit()
        self.cover_land.textChanged.connect(lambda: self.update_landscape_cover())
        self.landscape_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        )
        self.landscape_button.clicked.connect(lambda: self.select_landscape_cover())

        layout.addWidget(self.cover_land)
        layout.addWidget(self.landscape_button)
        return layout

    def select_landscape_cover(self):
        dirname = Path(self.cover_land.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="cover", directory=str(dirname), filter="Supported Image Files (*.png;*.jpeg;*.jpg)"
        )
        if not filename or not filename[0]:
            return
        self.cover_land.setText(filename[0])
        self.update_landscape_cover()

    def update_landscape_cover(self, cover_path=None):
        if cover_path:
            cover = cover_path
        else:
            cover = self.cover_land.text().strip()
        if not cover:
            self.landscape.setPixmap(QtGui.QPixmap())
            self.main.page_update()
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
            logger.exception("Bad image")
            self.cover_land.setText("")
        else:
            self.main.page_update()

    @staticmethod
    def image_type(file):
        mime_type = "image/jpeg"
        ext_type = "jpg"
        if file.lower().endswith("png"):
            mime_type = "image/png"
            ext_type = "png"
        return mime_type, ext_type

    def generate_attachment(self, filename, track_index=0):
        attr = getattr(self, f"{filename}_path", None)
        cover_image = None
        if attr:
            cover_image = attr.text()
        if getattr(self, f"{filename}_passthrough_checkbox").isChecked():
            cover_image = str(Path(self.main.path.work) / self.attachments[filename].name)
        if cover_image:
            mime_type, ext_type = self.image_type(cover_image)
            return (
                f' -attach "{cover_image}" -metadata:s:{track_index} mimetype={mime_type} '
                f'-metadata:s:{track_index}  filename="{filename}.{ext_type}" '
            )

    def get_settings(self, out_stream_start_index=0):
        track_index = out_stream_start_index
        commands = []

        for filename in ("cover", "cover_land", "small_cover", "small_cover_land"):
            command = self.generate_attachment(filename, track_index=track_index)
            if command:
                track_index += 1
                commands.append(command)

        return Box(
            attachments=re.sub("[ ]+", " ", " ".join(commands)),
            attachments_track_count=track_index - out_stream_start_index,
        )

    def cover_passthrough_check(self):
        checked = self.cover_passthrough_checkbox.isChecked()
        if checked:
            self.cover_path.setDisabled(True)
            self.cover_button.setDisabled(True)
            pixmap = QtGui.QPixmap(str(Path(self.main.path.work) / self.attachments.cover.name))
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
        if checked:
            self.cover_land.setDisabled(True)
            self.landscape_button.setDisabled(True)
            pixmap = QtGui.QPixmap(str(Path(self.main.path.work) / self.attachments.cover_land.name))
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.landscape.setPixmap(pixmap)
        else:
            self.cover_land.setDisabled(False)
            self.landscape_button.setDisabled(False)
            if not self.cover_land.text() or not Path(self.cover_land.text()).exists():
                self.landscape.setPixmap(QtGui.QPixmap())
            else:
                pixmap = QtGui.QPixmap(self.cover_land.text())
                pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
                self.landscape.setPixmap(pixmap)

        self.main.page_update(build_thumbnail=False)

    def small_cover_land_passthrough_check(self):
        self.main.page_update(build_thumbnail=False)

    def new_source(self, attachments):

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
        self.cover_land.setDisabled(False)
        self.cover_land.setText("")
        self.landscape_button.setDisabled(False)

        for attachment in attachments:
            filename = attachment.get("tags", {}).get("filename", "")
            base_name = filename.rsplit(".", 1)[0]
            file_path = Path(self.main.path.work) / filename
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
                self.cover_land.setDisabled(True)
                self.cover_land.setText("")
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
