#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box, BoxList

from fastflix.shared import QtWidgets
from fastflix.widgets.panels.command_panel import CommandList
from fastflix.widgets.panels.audio_panel import AudioList
from fastflix.widgets.panels.subtitle_panel import SubtitleList

logger = logging.getLogger("fastflix")


class VideoOptions(QtWidgets.QTabWidget):
    def __init__(self, parent, available_audio_encoders):
        super().__init__(parent)
        self.main = parent

        self.selected = 0

        self.commands = CommandList(self)
        self.current_plugin = list(self.main.plugins.values())[0]
        self.current_settings = self.current_plugin.settings_panel(self, self.main)

        self.audio = AudioList(self, available_audio_encoders)
        self.subtitles = SubtitleList(self)
        # self.subtitles.hide()
        self.addTab(self.current_settings, "Quality")
        self.addTab(self.audio, "Audio")
        self.addTab(self.subtitles, "Subtitles")
        self.addTab(self.commands, "Command List")

    def change_conversion(self, conversion):
        self.current_settings.close()
        self.current_plugin = self.main.plugins[conversion]
        self.current_settings = self.current_plugin.settings_panel(self, self.main)
        self.current_settings.show()
        self.removeTab(0)
        self.insertTab(0, self.current_settings, "Quality")
        self.setCurrentIndex(0)
        self.setTabEnabled(1, getattr(self.current_plugin, "enable_audio", True))
        self.setTabEnabled(2, getattr(self.current_plugin, "enable_subtitles", True))
        self.selected = conversion
        self.audio.allowed_formats(self.current_plugin.audio_formats)
        self.current_settings.new_source()
        self.main.page_update()

    def get_settings(self):
        settings = Box()
        settings.update(self.current_settings.get_settings())
        if getattr(self.current_plugin, "enable_audio", True):
            settings.update(self.audio.get_settings())
        if getattr(self.current_plugin, "enable_subtitles", True):
            settings.update(self.subtitles.get_settings())
        return settings

    def new_source(self):
        if getattr(self.current_plugin, "enable_audio", True):
            self.audio.new_source(self.current_plugin.audio_formats, starting_pos=1)
        if getattr(self.current_plugin, "enable_subtitles", True):
            self.subtitles.new_source(starting_pos=len(self.audio) + 1)
        self.current_settings.new_source()

    def refresh(self):
        if getattr(self.current_plugin, "enable_audio", True):
            self.audio.refresh(starting_pos=1)
        if getattr(self.current_plugin, "enable_subtitles", True):
            self.subtitles.refresh(starting_pos=len(self.audio) + 1)
