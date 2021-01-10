#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from typing import List, Union
from itertools import chain

from box import Box, BoxList
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import AttachmentTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import link

logger = logging.getLogger("fastflix")


class DebugPanel(QtWidgets.QTabWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.reset()

    def get_textbox(self, obj: Union["Box", "BoxList"]) -> "QtWidgets.QTextBrowser":
        widget = QtWidgets.QTextBrowser(self)
        widget.setReadOnly(True)
        widget.setDisabled(False)
        widget.setText(obj.to_yaml(default_flow_style=False))
        return widget

    def get_ffmpeg_details(self):
        data = {
            "ffmpeg version": self.app.fastflix.ffmpeg_version,
            "ffprobe version": self.app.fastflix.ffprobe_version,
            "ffmpeg config": self.app.fastflix.ffmpeg_config,
        }
        return data

    def reset(self):
        for i in range(self.count() - 1, -1, -1):
            self.removeTab(i)

        self.addTab(self.get_textbox(Box(self.app.fastflix.config.dict())), "Config")
        self.addTab(self.get_textbox(Box(self.get_ffmpeg_details())), "FFmpeg Details")
        self.addTab(self.get_textbox(BoxList(self.app.fastflix.queue)), "Queue")
        self.addTab(self.get_textbox(Box(self.app.fastflix.encoders)), "Encoders")
        self.addTab(self.get_textbox(BoxList(self.app.fastflix.audio_encoders)), "Audio Encoders")
        if self.app.fastflix.current_video:
            self.addTab(self.get_textbox(BoxList(self.app.fastflix.current_video)), "Current Video")
