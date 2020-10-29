#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box, BoxList
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.widgets.panels.audio_panel import AudioList
from fastflix.widgets.panels.command_panel import CommandList
from fastflix.widgets.panels.cover_panel import CoverPanel
from fastflix.widgets.panels.status_panel import StatusPanel
from fastflix.widgets.panels.subtitle_panel import SubtitleList

logger = logging.getLogger("fastflix")


class VideoOptions(QtWidgets.QTabWidget):
    def __init__(self, parent, available_audio_encoders, log_queue):
        super().__init__(parent)
        self.main = parent

        self.selected = 0
        self.commands = CommandList(self)
        self.current_settings = self.main.current_encoder.settings_panel(self, self.main)

        self.audio = AudioList(self, available_audio_encoders)
        self.subtitles = SubtitleList(self)
        self.status = StatusPanel(self, log_queue)
        self.attachments = CoverPanel(self)
        # self.subtitles.hide()
        self.addTab(self.current_settings, "Quality")
        self.addTab(self.audio, "Audio")
        self.addTab(self.subtitles, "Subtitles")
        self.addTab(self.attachments, "Cover")
        self.addTab(self.commands, "Command List")
        self.addTab(self.status, "Encoding Status")

    @property
    def audio_formats(self):
        plugin_formats = set(self.main.current_encoder.audio_formats)
        if self.main.config.get("use_sane_audio") and self.main.config.get("sane_audio_selection"):
            return list(plugin_formats & set(self.main.config.sane_audio_selection))
        return list(plugin_formats)

    def change_conversion(self, conversion):
        conversion = conversion.strip()
        self.current_settings.close()
        self.main.current_encoder = self.main.plugins[conversion]
        self.current_settings = self.main.current_encoder.settings_panel(self, self.main)
        self.current_settings.show()
        self.removeTab(0)
        self.insertTab(0, self.current_settings, "Quality")
        self.setCurrentIndex(0)
        self.setTabEnabled(1, getattr(self.main.current_encoder, "enable_audio", True))
        self.setTabEnabled(2, getattr(self.main.current_encoder, "enable_subtitles", True))
        self.setTabEnabled(3, getattr(self.main.current_encoder, "enable_attachments", True))
        self.selected = conversion
        self.audio.allowed_formats(self.audio_formats)
        self.current_settings.new_source()
        self.main.page_update()

    def get_settings(self):
        settings = Box()
        settings.update(self.current_settings.get_settings())
        tracks = 1
        if getattr(self.main.current_encoder, "enable_audio", False):
            audio_settings = self.audio.get_settings()
            tracks += audio_settings.audio_track_count
            settings.update(audio_settings)
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            subtitle_settings = self.subtitles.get_settings()
            tracks += subtitle_settings.subtitle_track_count
            settings.update(subtitle_settings)
        if getattr(self.main.current_encoder, "enable_attachments", False):
            settings.update(self.attachments.get_settings(out_stream_start_index=tracks))
        return settings

    def new_source(self):
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.new_source(self.audio_formats, starting_pos=1)
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.new_source(starting_pos=len(self.audio) + 1)
        if getattr(self.main.current_encoder, "enable_attachments", False):
            self.attachments.new_source(self.main.streams.attachment)
        self.current_settings.new_source()

    def refresh(self):
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.refresh(starting_pos=1)
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.refresh(starting_pos=len(self.audio) + 1)
