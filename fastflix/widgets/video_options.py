#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import logging

from qtpy import QtGui, QtWidgets, QtCore

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon
from fastflix.shared import DEVMODE, error_message
from fastflix.widgets.panels.advanced_panel import AdvancedPanel
from fastflix.widgets.panels.audio_panel import AudioList
from fastflix.widgets.panels.command_panel import CommandList
from fastflix.widgets.panels.cover_panel import CoverPanel
from fastflix.widgets.panels.debug_panel import DebugPanel
from fastflix.widgets.panels.info_panel import InfoPanel
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
        self.advanced = AdvancedPanel(self, self.app)
        self.info = InfoPanel(self, self.app)
        self.debug = DebugPanel(self, self.app)
        if self.app.fastflix.config.theme == "onyx":
            self.setStyleSheet("background-color: #4b5054; color: white;")

        self.addTab(self.current_settings, QtGui.QIcon(get_icon("editing", app.fastflix.config.theme)), t("Quality"))
        self.addTab(self.audio, QtGui.QIcon(get_icon("music", app.fastflix.config.theme)), t("Audio"))
        self.addTab(self.subtitles, QtGui.QIcon(get_icon("cc", app.fastflix.config.theme)), t("Subtitles"))
        self.addTab(self.attachments, QtGui.QIcon(get_icon("photo", app.fastflix.config.theme)), t("Cover"))
        self.addTab(self.advanced, QtGui.QIcon(get_icon("advanced", app.fastflix.config.theme)), t("Advanced"))
        self.addTab(self.info, QtGui.QIcon(get_icon("info", app.fastflix.config.theme)), t("Source Details"))
        self.addTab(self.commands, QtGui.QIcon(get_icon("text-left", app.fastflix.config.theme)), t("Raw Commands"))
        self.addTab(self.status, QtGui.QIcon(get_icon("working", app.fastflix.config.theme)), t("Encoding Status"))
        self.addTab(self.queue, QtGui.QIcon(get_icon("poll", app.fastflix.config.theme)), t("Encoding Queue"))
        if DEVMODE:
            self.addTab(self.debug, QtGui.QIcon(get_icon("info", app.fastflix.config.theme)), "Debug")

    def paintEvent(self, event):
        o = QtWidgets.QStyleOption()
        o.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, o, p, self)

    def _get_audio_formats(self, encoder=None):
        encoders = None
        if encoder:
            if getattr(self.main.current_encoder, "audio_formats", None):
                encoders = set(self.main.current_encoder.audio_formats)
        elif getattr(self.main.current_encoder, "audio_formats", None):
            encoders = set(self.main.current_encoder.audio_formats)
        if encoders is None:
            encoders = set(self.app.fastflix.audio_encoders)
        if self.app.fastflix.config.use_sane_audio and self.app.fastflix.config.sane_audio_selection:
            return list(encoders & set(self.app.fastflix.config.sane_audio_selection))
        return list(encoders)

    @property
    def audio_formats(self):
        return self._get_audio_formats()

    def change_conversion(self, conversion):
        conversion = conversion.strip()
        encoder = self.app.fastflix.encoders[conversion]
        self.current_settings.close()
        self.current_settings = encoder.settings_panel(self, self.main, self.app)
        self.current_settings.show()
        self.removeTab(0)
        self.insertTab(0, self.current_settings, t("Quality"))
        self.setTabIcon(0, QtGui.QIcon(get_icon("editing", self.app.fastflix.config.theme)))
        self.setCurrentIndex(0)
        self.setTabEnabled(1, getattr(encoder, "enable_audio", True))
        self.setTabEnabled(2, getattr(encoder, "enable_subtitles", True))
        self.setTabEnabled(3, getattr(encoder, "enable_attachments", True))
        self.selected = conversion
        self.current_settings.new_source()
        self.main.page_update(build_thumbnail=False)
        if (
            self.app.fastflix.current_video
            and not getattr(self.main.current_encoder, "enable_concat", False)
            and self.app.fastflix.current_video.concat
        ):
            error_message(
                f"This encoder, {self.main.current_encoder.name} does not support concatenating files together"
            )
        # Page update does a reload which bases itself off the current encoder so we have to do audio formats after
        self.audio.allowed_formats(self._get_audio_formats(encoder))

    def get_settings(self):
        if not self.app.fastflix.current_video:
            return
        self.current_settings.update_video_encoder_settings()

        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.update_audio_settings()
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.get_settings()
        if getattr(self.main.current_encoder, "enable_attachments", False):
            self.attachments.update_cover_settings()

        self.advanced.update_settings()
        self.main.container.profile.update_settings()

    def new_source(self):
        if not self.app.fastflix.current_video:
            return
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.new_source(self.audio_formats)
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.new_source()
        if getattr(self.main.current_encoder, "enable_attachments", False):
            self.attachments.new_source(self.app.fastflix.current_video.streams.attachment)
        self.current_settings.new_source()
        self.queue.new_source()
        self.advanced.new_source()
        self.main.container.profile.update_settings()
        self.info.reset()
        self.debug.reset()

    def refresh(self):
        if getattr(self.main.current_encoder, "enable_audio", False):
            self.audio.refresh()
        if getattr(self.main.current_encoder, "enable_subtitles", False):
            self.subtitles.refresh()
        self.advanced.update_settings()
        self.main.container.profile.update_settings()

    def update_profile(self):
        self.current_settings.update_profile()
        if self.app.fastflix.current_video:
            if getattr(self.main.current_encoder, "enable_audio", False):
                self.audio.update_audio_settings()
            if getattr(self.main.current_encoder, "enable_subtitles", False):
                self.subtitles.get_settings()
            if getattr(self.main.current_encoder, "enable_attachments", False):
                self.attachments.update_cover_settings()
        self.advanced.update_settings()
        self.main.container.profile.update_settings()

    def reload(self):
        self.change_conversion(self.app.fastflix.current_video.video_settings.video_encoder_settings.name)
        self.main.widgets.convert_to.setCurrentIndex(
            list(self.app.fastflix.encoders.keys()).index(
                self.app.fastflix.current_video.video_settings.video_encoder_settings.name
            )
        )
        try:
            self.current_settings.reload()
        except Exception:
            logger.exception("Should not have happened, could not reload from queue")
            return
        if self.app.fastflix.current_video:
            streams = copy.deepcopy(self.app.fastflix.current_video.streams)
            settings = copy.deepcopy(self.app.fastflix.current_video.video_settings)
            audio_tracks = settings.audio_tracks
            subtitle_tracks = settings.subtitle_tracks
            try:
                if getattr(self.main.current_encoder, "enable_audio", False):
                    self.audio.reload(audio_tracks, self.audio_formats)
                if getattr(self.main.current_encoder, "enable_subtitles", False):
                    self.subtitles.reload(subtitle_tracks)
                if getattr(self.main.current_encoder, "enable_attachments", False):
                    self.attachments.reload_from_queue(streams, settings)
                self.advanced.reset(settings=settings)
                self.info.reset()
            except Exception:
                logger.exception("Should not have happened, could not reload from queue")
                return
        self.debug.reset()

    def clear_tracks(self):
        self.current_settings.update_profile()
        self.audio.remove_all()
        self.subtitles.remove_all()
        self.attachments.clear_covers()
        self.commands.update_commands([])
        self.advanced.reset()
        self.info.reset()
        self.debug.reset()

    def update_queue(self):
        self.queue.new_source()

    def show_queue(self):
        self.setCurrentWidget(self.queue)

    def show_status(self):
        self.setCurrentWidget(self.status)

    def cleanup(self):
        self.status.cleanup()

    def settings_update(self):
        if getattr(self.current_settings, "setting_change", False):
            self.current_settings.setting_change()
        self.debug.reset()
