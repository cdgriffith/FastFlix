#!/usr/bin/env python
import logging

from box import Box, BoxList

from flix.shared import QtWidgets
from flix.widgets.panels.command_panel import CommandList
from flix.widgets.panels import gif, vp9
from flix.widgets.panels.audio_panel import AudioList
from flix.widgets.panels.subtitle_panel import SubtitleList

logger = logging.getLogger('flix')


class VideoOptions(QtWidgets.QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.main = parent

        self.converters = BoxList([
             {'name': 'GIF', 'quality': gif.GIF(self, self.main), 'audio': False, 'subtitles': False},
             {'name': 'VP9', 'quality': vp9.VP9(self, self.main), 'audio': True, 'subtitles': True},
             #{'quality': QtWidgets.QWidget()}
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
        for converter in self.converters:
            converter.quality.hide()
        options = self.converters[conversion]
        options.quality.show()
        self.removeTab(0)
        self.insertTab(0, options.quality, "Quality")
        self.setCurrentIndex(0)
        self.setTabEnabled(1, options.get('audio', True))
        self.setTabEnabled(2, options.get('subtitles', True))
        self.selected = conversion
        options.quality.new_source()

    def get_settings(self):
        settings = Box()
        options = self.converters[self.selected]
        settings.update(options.quality.get_settings())
        if options.get('audio', True):
            settings.update(self.audio.get_settings())
        return settings

    def new_source(self):
        self.audio.new_source()
        self.converters[self.selected].quality.new_source()

