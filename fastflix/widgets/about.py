#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

import reusables
from box import __version__ as box_version
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.shared import base_path, link, pyinstaller
from fastflix.version import __version__

__all__ = ["About"]


class About(QtWidgets.QWidget):
    def __init__(self, app):
        super(About, self).__init__()
        layout = QtWidgets.QGridLayout()
        self.app = app
        self.setMinimumSize(QtCore.QSize(400, 400))

        build_file = Path(base_path, "build_version")

        build = t("Build")
        label = QtWidgets.QLabel(
            f"<b>FastFlix</b> v{__version__}<br>"
            f"{f'{build}: {build_file.read_text().strip()}<br>' if build_file.exists() else ''}"
            f"<br>{t('Author')}: {link('https://github.com/cdgriffith', 'Chris Griffith', app.fastflix.config.theme)}"
            f"<br>{t('License')}: MIT"
        )
        label.setFont(QtGui.QFont(self.app.font().family(), 14))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setOpenExternalLinks(True)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(label)

        bundle_label = QtWidgets.QLabel(
            f"{t('Conversion suites')}: {link('https://www.ffmpeg.org/download.html', 'FFmpeg', app.fastflix.config.theme)} ({t('Various')}), "
            f"{link('https://github.com/rigaya/NVEnc', 'NVEncC', app.fastflix.config.theme)} (MIT) "
            f"{link('https://github.com/rigaya/QSVEnc', 'QSVEnc', app.fastflix.config.theme)} (MIT) "
            f"{link('https://github.com/rigaya/VCEEnc', 'VCEEnc', app.fastflix.config.theme)} (MIT)<br><br>"
            f"{t('Encoders')}: <br> {link('https://github.com/rigaya/NVEnc', 'NVEncC', app.fastflix.config.theme)} (MIT), "
            f"{link('https://github.com/rigaya/VCEEnc', 'VCEEnc', app.fastflix.config.theme)} (MIT), "
            f"{link('https://github.com/rigaya/QSVEnc', 'QSVEnc', app.fastflix.config.theme)} (MIT), "
            f"SVT AV1 (MIT), rav1e (MIT), aom (MIT), x265 (GPL), x264 (GPL), libvpx (BSD)"
        )
        bundle_label.setAlignment(QtCore.Qt.AlignCenter)
        bundle_label.setOpenExternalLinks(True)
        layout.addWidget(bundle_label)

        supporting_libraries_label = QtWidgets.QLabel(
            f"{t('Supporting libraries')}<br>"
            f"{link('https://www.python.org/', t('Python'), app.fastflix.config.theme)}{reusables.version_string} (PSF LICENSE), "
            f"{link('https://github.com/cdgriffith/Box', t('python-box'), app.fastflix.config.theme)} {box_version} (MIT), "
            f"{link('https://github.com/cdgriffith/Reusables', t('Reusables'), app.fastflix.config.theme)} {reusables.__version__} (MIT)<br>"
            "mistune (BSD), colorama (BSD), coloredlogs (MIT), Requests (Apache 2.0)<br>"
            "appdirs (MIT), iso639-lang (MIT), psutil (BSD), pathvalidate (MIT) <br>"
            "BreezeStyleSheets (MIT), PySide6 (LGPL)"
        )
        supporting_libraries_label.setAlignment(QtCore.Qt.AlignCenter)
        supporting_libraries_label.setOpenExternalLinks(True)
        layout.addWidget(supporting_libraries_label)

        if pyinstaller:
            pyinstaller_label = QtWidgets.QLabel(
                f"{t('Packaged with')}: {link('https://www.pyinstaller.org/index.html', 'PyInstaller', app.fastflix.config.theme)}"
            )
            pyinstaller_label.setAlignment(QtCore.Qt.AlignCenter)
            pyinstaller_label.setOpenExternalLinks(True)
            layout.addWidget(QtWidgets.QLabel())
            layout.addWidget(pyinstaller_label)

        license_label = QtWidgets.QLabel(
            link(
                "https://github.com/cdgriffith/FastFlix/blob/master/docs/build-licenses.txt",
                t("LICENSES"),
                app.fastflix.config.theme,
            )
        )
        license_label.setAlignment(QtCore.Qt.AlignCenter)
        license_label.setOpenExternalLinks(True)
        layout.addWidget(QtWidgets.QLabel())
        layout.addWidget(license_label)

        self.setLayout(layout)
