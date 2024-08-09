#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Union

from box import Box, BoxList
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.models.fastflix_app import FastFlixApp
from fastflix.shared import DEVMODE

logger = logging.getLogger("fastflix")


class DebugPanel(QtWidgets.QTabWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        if not DEVMODE:
            self.hide()
            return
        self.addTab(self.get_textbox(Box(self.app.fastflix.config.model_dump())), "Config")
        self.addTab(self.get_textbox(Box(self.get_ffmpeg_details())), "FFmpeg Details")
        self.addTab(self.get_textbox(BoxList(self.app.fastflix.conversion_list)), "Queue")
        self.addTab(self.get_textbox(Box(self.app.fastflix.encoders)), "Encoders")
        self.addTab(self.get_textbox(BoxList(self.app.fastflix.audio_encoders)), "Audio Encoders")
        if self.app.fastflix.current_video:
            self.cv = self.get_textbox(Box(self.app.fastflix.current_video.model_dump()))
            self.addTab(self.cv, "Current Video")

    def get_textbox(self, obj: Union["Box", "BoxList"]) -> "QtWidgets.QTextBrowser":
        widget = QtWidgets.QTextBrowser(self)
        widget.setReadOnly(True)
        widget.setDisabled(False)
        widget.setText(obj.to_yaml(default_flow_style=False, ruamel_typ="unsafe"))
        return widget

    def get_ffmpeg_details(self):
        data = {
            "ffmpeg version": self.app.fastflix.ffmpeg_version,
            "ffprobe version": self.app.fastflix.ffprobe_version,
            "ffmpeg config": self.app.fastflix.ffmpeg_config,
        }
        return data

    def reset(self):
        if not DEVMODE:
            return
        # for i in range(self.count() - 1, -1, -1):
        #     self.removeTab(i)

        if self.app.fastflix.current_video:
            if hasattr(self, "cv"):
                self.removeTab(self.count() - 1)
                self.cv.close()
                del self.cv
            self.cv = self.get_textbox(Box(self.app.fastflix.current_video.model_dump()))
            self.addTab(self.cv, "Current Video")
