#!/usr/bin/env python
import logging
import os

from flix.shared import QtWidgets, QtGui, pyinstaller, base_path, message
from flix.widgets.av1 import AV1
from flix.widgets.x265 import X265
from flix.widgets.gif import GIF
from flix.widgets.logs import Logs
from flix.widgets.about import About
from flix.widgets.settings import Settings
from flix.flix import Flix
from flix.version import __version__

logger = logging.getLogger('flix')


class Main(QtWidgets.QMainWindow):

    def __init__(self, ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, svt_av1, source="", parent=None):
        super(Main, self).__init__(parent)
        self.x265 = X265(parent=self, source=source)
        self.av1 = AV1(parent=self, source=source)
        self.gif = GIF(parent=self, source=source)
        self.x265.show()
        self.av1.show()

        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.svt_av1 = svt_av1
        self.ffmpeg_version = ffmpeg_version
        self.ffprobe_version = ffprobe_version

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)
        self.default_status()

        self.settings = Settings(self)

        tab_widget = QtWidgets.QTabWidget()
        tab_widget.addTab(self.gif, "GIF")
        tab_widget.addTab(self.av1, "AV1")
        tab_widget.addTab(self.x265, "x265")
        tab_widget.addTab(Logs(self), 'Logs')
        tab_widget.addTab(self.settings, 'Settings')
        tab_widget.addTab(About(self), 'About')

        self.setCentralWidget(tab_widget)

        self.setWindowIcon(QtGui.QIcon(os.path.join(base_path, 'data/icon.ico') if pyinstaller else
                                       os.path.join(os.path.dirname(__file__), '../data/icon.ico')))

        if not ffmpeg_version or not ffprobe_version:
            self.x265.setDisabled(True)
            tab_widget.setCurrentIndex(3)
            message("You need to select ffmpeg and ffprobe or equivalent tools to use before you can encode.",
                    parent=self)

        if 'libx265' not in Flix(ffmpeg=ffmpeg).ffmpeg_configuration():
            self.x265.setDisabled(True)
            tab_widget.setCurrentIndex(2)

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
        if self.x265.encoding_worker and self.x265.encoding_worker.is_alive():
            self.x265.encoding_worker.kill()
        try:
            os.remove(self.x265.thumb_file)
        except OSError:
            pass
        event.accept()

    def disable_converters(self, converters=('x265', 'av1')):
        if isinstance(converters, str):
            return getattr(self, converters).setDisabled(True)
        for converter in converters:
            getattr(self, converter).setDisabled(True)

    def enable_converters(self, converters=('x265', 'av1')):
        if isinstance(converters, str):
            return getattr(self, converters).setDisabled(False)
        for converter in converters:
            getattr(self, converter).setDisabled(False)

    def get_settings(self):
        return self.settings.get_settings()
