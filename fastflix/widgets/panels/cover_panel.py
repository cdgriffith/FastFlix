#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
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

        info = QtWidgets.QLabel()
        info.setPixmap(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning).pixmap(16, 16))
        info.setToolTip(
            "Hardly any system supports MKV's covers as thumbnails by default<br><br> "
            "Windows needs the ICAROS shell extension with proper settings applied <br><br> "
            "Android / Google products do not support covers <br>"
            ""
        )

        # row, column, row span, column span
        layout.addWidget(QtWidgets.QLabel("Poster Cover"), 0, 0, 1, 5)
        layout.addWidget(QtWidgets.QLabel("Landscape Cover"), 0, 6, 1, 4)
        layout.addWidget(info, 0, 9, 1, 1, QtCore.Qt.AlignRight)

        poster_options_layout = QtWidgets.QHBoxLayout()
        self.cover_passthrough_checkbox = QtWidgets.QCheckBox("Copy Cover")
        self.small_cover_passthrough_checkbox = QtWidgets.QCheckBox("Copy Small Cover (no preview)")

        poster_options_layout.addWidget(self.cover_passthrough_checkbox)
        poster_options_layout.addWidget(self.small_cover_passthrough_checkbox)

        land_options_layout = QtWidgets.QHBoxLayout()
        self.land_passthrough_checkbox = QtWidgets.QCheckBox("Copy Landscape Cover")
        self.small_land_passthrough_checkbox = QtWidgets.QCheckBox("Copy Small Landscape Cover  (no preview)")

        land_options_layout.addWidget(self.land_passthrough_checkbox)
        land_options_layout.addWidget(self.small_land_passthrough_checkbox)

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
        self.landscape_cover_path = QtWidgets.QLineEdit()
        self.landscape_cover_path.textChanged.connect(lambda: self.update_landscape_cover())
        self.landscape_button = QtWidgets.QPushButton(
            icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
        )
        self.landscape_button.clicked.connect(lambda: self.select_landscape_cover())

        layout.addWidget(self.landscape_cover_path)
        layout.addWidget(self.landscape_button)
        return layout

    def select_landscape_cover(self):
        dirname = Path(self.landscape_cover_path.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="cover", directory=str(dirname), filter="Supported Image Files (*.png;*.jpeg;*.jpg)"
        )
        if not filename or not filename[0]:
            return
        self.landscape_cover_path.setText(filename[0])
        self.update_landscape_cover()

    def update_landscape_cover(self, cover_path=None):
        if cover_path:
            cover = cover_path
        else:
            cover = self.landscape_cover_path.text().strip()
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
            self.landscape_cover_path.setText("")
        else:
            self.main.page_update()

    def get_settings(self):

        idx = 0
        commands = []
        if self.cover_passthrough_checkbox.isChecked():
            commands.append(f" -map 0:{self.attachments.cover.stream}")
        elif self.cover_path.text():
            cover_mime_type = "image/jpeg"
            cover_ext_type = "jpg"
            if self.cover_path.text().lower().endswith("png"):
                cover_mime_type = "image/png"
                cover_ext_type = "png"
            commands.append(
                f' -attach "{self.cover_path.text()}" -metadata:s:t:{idx} mimetype={cover_mime_type} '
                f'-metadata:s:t:{idx} filename="cover.{cover_ext_type}" '
            )
            idx += 1

        if self.land_passthrough_checkbox.isChecked():
            commands.append(f" -map 0:{self.attachments.cover_land.stream}")

        elif self.landscape_cover_path.text():
            cover_land_mime_type = "image/jpeg"
            cover_land_ext_type = "jpg"
            if self.landscape_cover_path.text().lower().endswith("png"):
                cover_land_mime_type = "image/png"
                cover_land_ext_type = "png"
            commands.append(
                f' -attach "{self.landscape_cover_path.text()}" -metadata:s:t:{idx} mimetype={cover_land_mime_type} '
                f'-metadata:s:t:{idx} filename="cover_land.{cover_land_ext_type}" '
            )

        if self.small_land_passthrough_checkbox.isChecked():
            commands.append(f" -map 0:{self.attachments.small_cover_land.stream}")
        if self.small_cover_passthrough_checkbox.isChecked():
            commands.append(f" -map 0:{self.attachments.small_cover.stream}")

        return {"attachments": "".join(commands)}

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
        checked = self.small_cover_passthrough_checkbox.isChecked()
        self.main.page_update(build_thumbnail=False)

    def land_passthrough_check(self):
        checked = self.land_passthrough_checkbox.isChecked()
        if checked:
            self.landscape_cover_path.setDisabled(True)
            self.landscape_button.setDisabled(True)
            pixmap = QtGui.QPixmap(str(Path(self.main.path.work) / self.attachments.cover_land.name))
            pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
            self.landscape.setPixmap(pixmap)
        else:
            self.landscape_cover_path.setDisabled(False)
            self.landscape_button.setDisabled(False)
            if not self.landscape_cover_path.text() or not Path(self.landscape_cover_path.text()).exists():
                self.landscape.setPixmap(QtGui.QPixmap())
            else:
                pixmap = QtGui.QPixmap(self.landscape_cover_path.text())
                pixmap = pixmap.scaled(230, 230, QtCore.Qt.KeepAspectRatio)
                self.landscape.setPixmap(pixmap)

        self.main.page_update(build_thumbnail=False)

    def small_land_passthrough_check(self):
        checked = self.small_land_passthrough_checkbox.isChecked()
        self.main.page_update(build_thumbnail=False)

    def new_source(self, attachments):

        self.cover_passthrough_checkbox.disconnect()
        self.small_cover_passthrough_checkbox.disconnect()
        self.land_passthrough_checkbox.disconnect()
        self.small_land_passthrough_checkbox.disconnect()

        self.cover_passthrough_checkbox.setChecked(False)
        self.small_cover_passthrough_checkbox.setChecked(False)
        self.land_passthrough_checkbox.setChecked(False)
        self.small_land_passthrough_checkbox.setChecked(False)

        self.cover_passthrough_checkbox.setDisabled(True)
        self.small_cover_passthrough_checkbox.setDisabled(True)
        self.land_passthrough_checkbox.setDisabled(True)
        self.small_land_passthrough_checkbox.setDisabled(True)
        self.attachments = Box()

        self.poster.setPixmap(QtGui.QPixmap())
        self.landscape.setPixmap(QtGui.QPixmap())

        self.cover_path.setDisabled(False)
        self.cover_path.setText("")
        self.cover_button.setDisabled(False)
        self.landscape_cover_path.setDisabled(False)
        self.landscape_cover_path.setText("")
        self.landscape_button.setDisabled(False)

        for attachment in attachments:
            filename = attachment.get("tags", {}).get("filename", "")
            base_name = filename.rsplit(".", 1)[0]
            if base_name == "cover":
                self.cover_passthrough_checkbox.setChecked(True)
                self.cover_passthrough_checkbox.setDisabled(False)
                self.update_cover(str(Path(self.main.path.work) / filename))
                self.cover_path.setDisabled(True)
                self.cover_path.setText("")
                self.cover_button.setDisabled(True)
                self.attachments.cover = {"name": filename, "stream": attachment.index}
            if base_name == "cover_land":
                self.land_passthrough_checkbox.setChecked(True)
                self.land_passthrough_checkbox.setDisabled(False)
                self.update_landscape_cover(str(Path(self.main.path.work) / filename))
                self.landscape_cover_path.setDisabled(True)
                self.landscape_cover_path.setText("")
                self.landscape_button.setDisabled(True)
                self.attachments.cover_land = {"name": filename, "stream": attachment.index}
            if base_name == "small_cover":
                self.small_cover_passthrough_checkbox.setChecked(True)
                self.small_cover_passthrough_checkbox.setDisabled(False)
                self.attachments.small_cover = {"name": filename, "stream": attachment.index}
            if base_name == "small_cover_land":
                self.small_land_passthrough_checkbox.setChecked(True)
                self.small_land_passthrough_checkbox.setDisabled(False)
                self.attachments.small_cover_land = {"name": filename, "stream": attachment.index}

        self.cover_passthrough_checkbox.toggled.connect(lambda: self.cover_passthrough_check())
        self.small_cover_passthrough_checkbox.toggled.connect(lambda: self.small_cover_passthrough_check())
        self.land_passthrough_checkbox.toggled.connect(lambda: self.land_passthrough_check())
        self.small_land_passthrough_checkbox.toggled.connect(lambda: self.small_land_passthrough_check())
