#!/usr/bin/env python
import os
from pathlib import Path
import time
from datetime import timedelta
import logging
import tempfile

import reusables

from flix.flix import Flix
from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width
from flix.widgets.worker import Worker
from flix.widgets.settings import gif

logger = logging.getLogger('flix')


class VideoOptions(QtWidgets.QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent

        self.converters = [
             {'quality': gif.GIF(self)},
             {'quality': QtWidgets.QWidget()},
             {'quality': QtWidgets.QWidget()}
        ]

        self.addTab(self.converters[0]['quality'], "Quality")
        self.addTab(QtWidgets.QWidget(), "Audio")
        self.addTab(QtWidgets.QWidget(), "Subtitles")

    def change_conversion(self, conversion):
        self.removeTab(0)
        self.insertTab(0, self.converters[conversion]['quality'], "Quality")
        self.setCurrentIndex(0)
