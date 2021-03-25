#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import logging

from qtpy import QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import (
    advanced_icon,
    cc_icon,
    editing_icon,
    info_icon,
    music_icon,
    photo_icon,
    poll_icon,
    text_left_icon,
    working_icon,
)
from fastflix.shared import DEVMODE
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

        self.addTab(self.current_settings, QtGui.QIcon(editing_icon), t("Quality"))
        self.addTab(self.audio, QtGui.QIcon(music_icon), t("Audio"))
        self.addTab(self.subtitles, QtGui.QIcon(cc_icon), t("Subtitles"))
        self.addTab(self.attachments, QtGui.QIcon(photo_icon), t("Cover"))
        self.addTab(self.advanced, QtGui.QIcon(advanced_icon), t("Advanced"))
        self.addTab(self.info, QtGui.QIcon(info_icon), t("Source Details"))
        self.addTab(self.commands, QtGui.QIcon(text_left_icon), t("Raw Commands"))
        self.addTab(self.status, QtGui.QIcon(working_icon), t("Encoding Status"))
        self.addTab(self.queue, QtGui.QIcon(poll_icon), t("Encoding Queue"))
        if DEVMODE:
            self.addTab(self.debug, QtGui.QIcon(info_icon), "Debug")

    @property
    def audio_formats(self):
        plugin_formats = set(self.main.current_encoder.audio_formats)
        if self.app.fastflix.config.use_sane_audio and self.app.fastflix.config.sane_audio_selection:
            return list(plugin_formats & set(self.app.fastflix.config.sane_audio_selection))
        return list(plugin_formats)

    def change_conversion(self, conversion):
        conversion = conversion.strip()
        encoder = self.app.fastflix.encoders[conversion]
        self.current_settings.close()
        self.current_settings = encoder.settings_panel(self, self.main, self.app)
        self.current_settings.show()
        self.removeTab(0)
        self.insertTab(0, self.current_settings, t("Quality"))
        self.setTabIcon(0, QtGui.QIcon(editing_icon))
        self.setCurrentIndex(0)
        self.setTabEnabled(1, getattr(encoder, "enable_audio", True))
        self.setTabEnabled(2, getattr(encoder, "enable_subtitles", True))
        self.setTabEnabled(3, getattr(encoder, "enable_attachments", True))
        self.selected = conversion
        self.audio.allowed_formats(self.audio_formats)
        self.current_settings.new_source()
        self.main.page_update(build_thumbnail=False)

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
