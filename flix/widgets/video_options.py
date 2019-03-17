#!/usr/bin/env python
import os
from pathlib import Path
import time
from datetime import timedelta
import logging
import tempfile

import reusables
from box import Box, BoxList

from flix.flix import Flix
from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width
from flix.widgets.worker import Worker
from flix.widgets.command_panel import CommandList
from flix.widgets.settings import gif
from flix.widgets.audio_panel import AudioList
from flix.widgets.subtitle_panel import SubtitleList

logger = logging.getLogger('flix')


class VideoOptions(QtWidgets.QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent

        self.converters = BoxList([
             {'quality': gif.GIF(self, self.main), 'audio': False, 'subtitles': False},
             {'quality': QtWidgets.QWidget()},
             {'quality': QtWidgets.QWidget()}
        ])

        self.selected = 0

        self.commands = CommandList(self)

        self.audio = AudioList(self)
        self.subtitles = SubtitleList(self)
        self.addTab(self.converters[0]['quality'], "Quality")
        self.addTab(self.audio, "Audio")
        self.addTab(self.subtitles, "Subtitles")
        self.addTab(self.commands, "Command List")

        self.setTabEnabled(1, False)
        self.setTabEnabled(2, False)

    def change_conversion(self, conversion):
        options = self.converters[conversion]
        self.removeTab(0)
        self.insertTab(0, options.quality, "Quality")
        self.setCurrentIndex(0)
        self.setTabEnabled(1, options.get('audio', True))
        self.setTabEnabled(2, options.get('subtitles', True))
        self.selected = conversion

    def get_settings(self):
        settings = Box()
        settings.update(self.converters[self.selected].quality.get_settings())
        return settings

    def new_source(self):
        self.converters[self.selected].quality.new_source()
