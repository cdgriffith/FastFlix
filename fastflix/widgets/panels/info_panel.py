#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from itertools import chain
from pathlib import Path
from typing import Union

from box import Box, BoxList
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import AttachmentTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import link

logger = logging.getLogger("fastflix")


class InfoPanel(QtWidgets.QTabWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()

    def reset(self):
        for i in range(self.count() - 1, -1, -1):
            self.removeTab(i)

        if not self.app.fastflix.current_video:
            return

        all_stream = []
        for x in self.app.fastflix.current_video.streams.values():
            all_stream.extend(x)

        for stream in sorted(all_stream, key=lambda z: z["index"]):
            widget = QtWidgets.QTextBrowser(self)
            widget.setReadOnly(True)
            widget.setDisabled(False)
            widget.setText(Box(stream).to_yaml(default_flow_style=False))
            self.addTab(widget, f"{stream['index']}: {stream['codec_type'].title()} ({stream.get('codec_name', '')})")
