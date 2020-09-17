#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from qtpy import QtWidgets, QtCore, QtGui


class AttachmentPanel(QtWidgets.QWidget):
    # TODO what if they select wrong thing?
    # TODO support updating if they type something in
    # TODO add frame where images will appear
    # TODO allow passthrough of existing covers
    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent.main

        layout = QtWidgets.QGridLayout()

        sp = QtWidgets.QSizePolicy()
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)

        # row, column, row span, column span
        layout.addWidget(QtWidgets.QLabel("Poster Cover"), 0, 0, 1, 5)
        layout.addWidget(QtWidgets.QLabel("Landscape Cover"), 0, 6, 1, 5)

        self.poster = QtWidgets.QLabel("<Poster Cover>")
        self.poster.setSizePolicy(sp)

        self.landscape = QtWidgets.QLabel("<Landscape Cover>")
        self.landscape.setSizePolicy(sp)

        layout.addWidget(self.poster, 1, 0, 8, 5)
        layout.addWidget(self.landscape, 1, 6, 8, 5)

        layout.addLayout(self.init_cover(), 9, 0, 1, 4)
        layout.addLayout(self.init_landscape_cover(), 9, 6, 1, 4)

        self.setLayout(layout)

    def init_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.cover_path = QtWidgets.QLineEdit()
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
        pixmap = QtGui.QPixmap(filename[0])
        pixmap = pixmap.scaled(320, 320, QtCore.Qt.KeepAspectRatio)
        self.poster.setPixmap(pixmap)
        self.main.page_update()

    def init_landscape_cover(self):
        layout = QtWidgets.QHBoxLayout()
        self.landscape_cover_path = QtWidgets.QLineEdit()
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
        pixmap = QtGui.QPixmap(filename[0])
        pixmap = pixmap.scaled(320, 320, QtCore.Qt.KeepAspectRatio)
        self.landscape.setPixmap(pixmap)
        self.main.page_update()

    def get_settings(self):
        cover_land = self.landscape_cover_path.text()
        cover = self.cover_path.text()

        cover_mime_type = "image/jpeg"
        cover_ext_type = "jpg"
        if cover.endswith("png"):
            cover_mime_type = "image/png"
            cover_ext_type = "png"

        cover_land_mime_type = "image/jpeg"
        cover_land_ext_type = "jpg"
        if cover_land.endswith("png"):
            cover_land_mime_type = "image/png"
            cover_land_ext_type = "png"

        idx = 0
        command = ""
        if cover:
            command += f' -attach "{cover}" -metadata:s:t:{idx} mimetype={cover_mime_type} -metadata:s:t:{idx} filename="cover.{cover_ext_type}" '
            idx += 1
        if cover_land:
            command += f' -attach "{cover_land}" -metadata:s:t:{idx} mimetype={cover_land_mime_type} -metadata:s:t:{idx} filename="cover_land.{cover_land_ext_type}" '

        return {"attachments": command}
