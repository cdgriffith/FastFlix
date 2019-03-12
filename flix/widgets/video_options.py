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


logger = logging.getLogger('flix')


class VideoOptions(QtWidgets.QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent

        self.addTab(QtWidgets.QWidget(), "Quality")
        self.addTab(QtWidgets.QWidget(), "Audio")
        self.addTab(QtWidgets.QWidget(), "Subtitles")

