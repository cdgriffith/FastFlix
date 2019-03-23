#!/usr/bin/env python
import logging

from box import Box, BoxList

from flix.shared import QtWidgets
from flix.widgets.panels.command_panel import CommandList
from flix.widgets.panels.audio_panel import AudioList
from flix.widgets.panels.subtitle_panel import SubtitleList

logger = logging.getLogger('flix')


class VideoOptions(QtWidgets.QTabWidget):

    def __init__(self, parent, available_audio_encoders):
        super().__init__(parent)
        self.main = parent

        self.selected = 0

        self.commands = CommandList(self)
        self.current_plugin = self.main.plugins.values()[0]
        self.current_settings = self.current_plugin.settings_panel(self, self.main)

        self.audio = AudioList(self, available_audio_encoders)
        self.subtitles = SubtitleList(self)
        self.subtitles.hide()
        self.addTab(self.current_settings, "Quality")
        self.addTab(self.audio, "Audio")
        #self.addTab(self.subtitles, "Subtitles")
        self.addTab(self.commands, "Command List")

    def change_conversion(self, conversion):
        self.current_settings.close()
        self.current_plugin = self.main.plugins[conversion]
        self.current_settings = self.current_plugin.settings_panel(self, self.main)
        self.current_settings.show()
        self.removeTab(0)
        self.insertTab(0, self.current_settings, "Quality")
        self.setCurrentIndex(0)
        self.setTabEnabled(1, getattr(self.current_plugin, 'enable_audio', True))
        self.setTabEnabled(2, getattr(self.current_plugin, 'enable_subtitles', True))
        self.selected = conversion
        self.audio.allowed_formats(self.current_plugin.audio_formats)
        self.current_settings.new_source()

    def get_settings(self):
        settings = Box()
        settings.update(self.current_settings.get_settings())
        if getattr(self.current_plugin, 'enable_audio', True):
            settings.update(self.audio.get_settings())
        return settings

    def new_source(self):
        self.audio.new_source(self.current_plugin.audio_formats)
        self.current_settings.new_source()

