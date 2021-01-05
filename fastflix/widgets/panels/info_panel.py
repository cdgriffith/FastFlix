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

        # self.text_area.setText(Box(self.app.fastflix.current_video.streams).to_yaml(default_flow_style=False))

        for stream in sorted(all_stream, key=lambda z: z["index"]):
            widget = QtWidgets.QTextBrowser(self)
            widget.setReadOnly(True)
            widget.setDisabled(False)
            widget.setText(Box(stream).to_yaml(default_flow_style=False))
            self.addTab(widget, f"{stream['index']}: {stream['codec_type'].title()} ({stream.get('codec_name', '')})")

        #
        #     if not self.incoming_same_as_source.isChecked():
        #         self.app.fastflix.current_video.video_settings.source_fps = self.incoming_fps_widget.text()
        #     if not self.outgoing_same_as_source.isChecked():
        #         self.app.fastflix.current_video.video_settings.output_fps = self.outgoing_fps_widget.text()

    # def init_cover(self):
    #     layout = QtWidgets.QHBoxLayout()
    #     self.cover_path = QtWidgets.QLineEdit()
    #     self.cover_path.textChanged.connect(lambda: self.update_cover())
    #     self.cover_button = QtWidgets.QPushButton(
    #         icon=self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)
    #     )
    #     self.cover_button.clicked.connect(lambda: self.select_cover())
    #
    #     layout.addWidget(self.cover_path)
    #     layout.addWidget(self.cover_button)
    #     return layout

    # def update_filter_settings(self):
    #     self.app.fastflix.current_video.video_settings.attachment_tracks = attachments

    def new_source(self):
        pass
