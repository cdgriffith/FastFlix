#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path

from qtpy import QtWidgets, QtCore, QtGui

logger = logging.getLogger("fastflix")


class AttachmentPanel(QtWidgets.QWidget):
    # TODO allow passthrough of existing covers
    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent.main

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
        layout.addWidget(info, 0, 10, 1, 1)

        self.poster = QtWidgets.QLabel()
        self.poster.setSizePolicy(sp)

        self.landscape = QtWidgets.QLabel()
        self.landscape.setSizePolicy(sp)

        layout.addWidget(self.poster, 1, 0, 8, 5)
        layout.addWidget(self.landscape, 1, 6, 8, 5)

        layout.addLayout(self.init_cover(), 9, 0, 1, 4)
        layout.addLayout(self.init_landscape_cover(), 9, 6, 1, 4)
        layout.columnStretch(5)

        self.setLayout(layout)

    def init_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.cover_path = QtWidgets.QLineEdit()
        self.cover_path.textChanged.connect(lambda: self.update_cover())
        button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView))
        button.clicked.connect(lambda: self.select_cover())

        layout.addWidget(self.cover_path)
        layout.addWidget(button)
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

    def update_cover(self):
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
        button = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView))
        button.clicked.connect(lambda: self.select_landscape_cover())

        layout.addWidget(self.landscape_cover_path)
        layout.addWidget(button)
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

    def update_landscape_cover(self):
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
        cover_land = self.landscape_cover_path.text()
        cover = self.cover_path.text()

        cover_mime_type = "image/jpeg"
        cover_ext_type = "jpg"
        if cover.lower().endswith("png"):
            cover_mime_type = "image/png"
            cover_ext_type = "png"

        cover_land_mime_type = "image/jpeg"
        cover_land_ext_type = "jpg"
        if cover_land.lower().endswith("png"):
            cover_land_mime_type = "image/png"
            cover_land_ext_type = "png"

        idx = 0
        commands = []
        if cover:
            commands.append(f' -attach "{cover}" -metadata:s:t:{idx} mimetype={cover_mime_type} '
                            f'-metadata:s:t:{idx} filename="cover.{cover_ext_type}" ')
            idx += 1
        if cover_land:
            commands.append(f' -attach "{cover_land}" -metadata:s:t:{idx} mimetype={cover_land_mime_type} '
                            f'-metadata:s:t:{idx} filename="cover_land.{cover_land_ext_type}" ')

        return {"attachments": "".join(commands)}
