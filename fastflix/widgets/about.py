#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

import reusables
from box import __version__ as box_version

from fastflix.shared import QtWidgets, QtCore, QtGui, pyside_version, pyinstaller, base_path
from fastflix.version import __version__

__all__ = ["About"]


class About(QtWidgets.QWidget):

    # TODO add all licenses

    def __init__(self, parent=None):
        super(About, self).__init__(parent)
        layout = QtWidgets.QGridLayout()

        self.setMinimumSize(400, 400)

        build_file = Path(base_path, "build_version")

        label = QtWidgets.QLabel(
            f"<b>FastFlix</b> v{__version__}<br>"
            f"{f'Build: {build_file.read_text().strip()}<br>' if build_file.exists() else ''}"
            f"<br>Author: <a href='https://github.com/cdgriffith'>Chris Griffith</a>"
            f"<br>License: MIT"
        )
        label.setFont(QtGui.QFont("Arial", 14))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setOpenExternalLinks(True)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        supporting_libraries_label = QtWidgets.QLabel(
            "Supporting libraries<br>"
            f"<a href='https://www.python.org/'>Python</a> {reusables.version_string} (PSF LICENSE), "
            f"<a href='https://wiki.qt.io/Qt_for_Python'>PySide2</a> {pyside_version} (LGPLv3)<br>"
            f"<a href='https://github.com/cdgriffith/Box'>python-box</a> {box_version} (MIT), "
            f"<a href='https://github.com/cdgriffith/Reusables'>Reusables</a> {reusables.__version__} (MIT)<br>"
        )
        supporting_libraries_label.setAlignment(QtCore.Qt.AlignCenter)
        supporting_libraries_label.setOpenExternalLinks(True)

        layout.addWidget(label)
        layout.addWidget(supporting_libraries_label)

        if Path(base_path, "bundled").exists():
            bundle_label = QtWidgets.QLabel(
                "Bundled with: <a href='https://github.com/OpenVisualCloud/SVT-AV1'>SVT AV1</a> (Modified BSD) and "
                "<a href='https://www.ffmpeg.org/download.html'>ffmpeg</a> (LGPL)"
            )
            bundle_label.setAlignment(QtCore.Qt.AlignCenter)
            bundle_label.setOpenExternalLinks(True)
            layout.addWidget(bundle_label)

        if pyinstaller:
            pyinstaller_label = QtWidgets.QLabel(
                "Packaged with: <a href='https://www.pyinstaller.org/index.html'>" "PyInstaller</a>"
            )
            pyinstaller_label.setAlignment(QtCore.Qt.AlignCenter)
            pyinstaller_label.setOpenExternalLinks(True)
            layout.addWidget(pyinstaller_label)

        replacer = "\\"
        license_label = QtWidgets.QLabel(
            f"<a href='file:///{base_path.replace(replacer, '/')}/docs/build-licenses.txt' download>LICENSES</a>"
        )
        license_label.setAlignment(QtCore.Qt.AlignCenter)
        license_label.setOpenExternalLinks(True)
        layout.addWidget(license_label)

        self.setLayout(layout)
        self.show()
