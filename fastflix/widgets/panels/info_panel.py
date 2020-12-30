#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from typing import List, Union

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

        self.video_tab = QtWidgets.QTextBrowser(parent)
        self.video_tab.setReadOnly(True)
        self.video_tab.setDisabled(False)

        self.addTab(self.video_tab, "Video")

    def reset(self):

        if not self.app.fastflix.current_video:
            return
        # self.text_area.setText(Box(self.app.fastflix.current_video.streams).to_yaml(default_flow_style=False))
        self.video_tab.setText(BoxList(self.app.fastflix.current_video.streams.video).to_yaml(default_flow_style=False))

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
