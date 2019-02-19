#!/usr/bin/env python
import logging
import os

from flix.shared import QtWidgets, QtGui, pyinstaller, base_path, message
from flix.widgets.x265 import X265
from flix.widgets.logs import Logs
from flix.widgets.about import About
from flix.widgets.settings import Settings
from flix.version import __version__

logger = logging.getLogger('flix')


class Main(QtWidgets.QMainWindow):

    def __init__(self, ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, source="", parent=None):
        super(Main, self).__init__(parent)
        self.converter = X265(parent=self, source=source)
        self.converter.show()

        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.ffmpeg_version = ffmpeg_version
        self.ffprobe_version = ffprobe_version

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)
        self.default_status()

        tab_widget = QtWidgets.QTabWidget()
        tab_widget.addTab(self.converter, "x265")
        tab_widget.addTab(Logs(self), 'Logs')
        tab_widget.addTab(Settings(self), 'Settings')
        tab_widget.addTab(About(self), 'About')

        self.setCentralWidget(tab_widget)

        self.setWindowIcon(QtGui.QIcon(os.path.join(base_path, 'data/icon.ico') if pyinstaller else
                                       os.path.join(os.path.dirname(__file__), '../data/icon.ico')))

        if not ffmpeg_version or not ffprobe_version:
            self.converter.setDisabled(True)
            tab_widget.setCurrentIndex(2)
            message("You need to select ffmpeg and ffprobe or equivalent tools to use before you can encode.",
                    parent=self)

        logger.info(f"Initialized FastFlix v{__version__}")
        logger.debug(f"ffmpeg version: {self.ffmpeg_version}")
        logger.debug(f"ffprobe version: {self.ffprobe_version}")

    def default_status(self):
        if not self.ffprobe_version or not self.ffmpeg_version:
            self.status.showMessage("ENCODING DISABLED - Please setup ffmpeg and ffprobe paths in settings!")
        else:
            self.status.showMessage(f"Using ffmpeg version {self.ffmpeg_version},"
                                    f" ffprobe version {self.ffprobe_version}")

    def closeEvent(self, event):
        if self.converter.encoding_worker and self.converter.encoding_worker.is_alive():
            self.converter.encoding_worker.kill()
        try:
            os.remove(self.converter.thumb_file)
        except OSError:
            pass
        event.accept()
