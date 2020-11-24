#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box, BoxList
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.widgets.panels.audio_panel import AudioList
from fastflix.widgets.panels.command_panel import CommandList
from fastflix.widgets.panels.cover_panel import CoverPanel
from fastflix.widgets.panels.queue_panel import EncodingQueue
from fastflix.widgets.panels.status_panel import StatusPanel
from fastflix.widgets.panels.subtitle_panel import SubtitleList

logger = logging.getLogger("fastflix")


class VideoOptions(QtWidgets.QTabWidget):
    def __init__(self, parent, app: FastFlixApp, available_audio_encoders):
        super().__init__(parent)
        self.main = parent
        self.app = app

        self.selected = 0
        self.commands = CommandList(self, self.app)
        self.current_settings = self.main.current_encoder.settings_panel(self, self.main, self.app)

        self.audio = AudioList(self, self.app)
        self.subtitles = SubtitleList(self, self.app)
        self.status = StatusPanel(self, self.app)
        self.attachments = CoverPanel(self, self.app)
        self.queue = EncodingQueue(self, self.app)
        # self.subtitles.hide()
        self.addTab(self.current_settings, t("Quality"))
        self.addTab(self.audio, t("Audio"))
        self.addTab(self.subtitles, t("Subtitles"))
        self.addTab(self.attachments, t("Cover"))
        self.addTab(self.commands, t("Raw Commands"))
        self.addTab(self.status, t("Encoding Status"))
        self.addTab(self.queue, t("Encoding Queue"))

    @property
    def audio_formats(self):
        plugin_formats = set(self.main.current_encoder.audio_formats)
        if self.app.fastflix.config.use_sane_audio and self.app.fastflix.config.sane_audio_selection:
            return list(plugin_formats & set(self.app.fastflix.config.sane_audio_selection))
        return list(plugin_formats)

    def change_conversion(self, conversion):
        conversion = conversion.strip()
        self.current_settings.close()
        # self.main.current_encoder = self.main.plugins[conversion]
        self.current_settings = self.app.fastflix.encoders[conversion].settings_panel(self, self.main, self.app)
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
        self.main.page_update(build_thumbnail=False)

    def get_settings(self):
        self.current_settings.update_video_encoder_settings()

        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.update_audio_settings()
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.get_settings()
        if getattr(self.main.current_encoder, "enable_attachments", False):
            self.attachments.get_settings()

        self.main.container.profile.update_settings()

    def new_source(self):
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.new_source(self.audio_formats)
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.new_source()
        if getattr(self.main.current_encoder, "enable_attachments", False):
            self.attachments.new_source(self.app.fastflix.current_video.streams.attachment)
        self.current_settings.new_source()
        self.queue.new_source()
        self.main.container.profile.update_settings()

    def refresh(self):
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.refresh()
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.refresh()
        self.main.container.profile.update_settings()

    def update_profile(self):
        self.current_settings.update_profile()

    def update_queue(self, currently_encoding=False):
        self.queue.new_source(currently_encoding)

    def show_queue(self):
        self.setCurrentWidget(self.queue)

    def show_status(self):
        self.setCurrentWidget(self.status)
