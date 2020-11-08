#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box
from qtpy import QtCore, QtGui, QtWidgets
from iso639 import Lang

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import FastFlixInternalException, error_message, main_width
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.models.encode import SubtitleTrack
from fastflix.language import t


class EncodeItem(QtWidgets.QTabWidget):
    def __init__(self, parent, video: Video, index, first=False):
        self.loading = True
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.first = first
        self.last = False

        self.widgets = Box(
            title=QtWidgets.QLabel(f"{video.video_settings.output_path}"),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
        )

        self.setFixedHeight(60)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        # grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.title, 0, 1)
        # grid.addLayout(disposition_layout, 0, 4)
        # grid.addWidget(self.widgets.burn_in, 0, 5)
        # grid.addLayout(self.init_language(), 0, 6)
        # # grid.addWidget(self.init_extract_button(), 0, 6)
        # grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(grid)
        self.loading = False
        self.updating_burn = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(20)
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def set_outdex(self, outdex):
        pass

    @property
    def enabled(self):
        return True

    def update_enable(self):
        pass

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class EncodingQueue(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(app, parent, t("Queue"), "queue")
        self.main = parent.main
        self.app = app

    def new_source(self):
        for i, video in enumerate(self.app.fastflix.queue, start=1):
            self.tracks.append(EncodeItem(self, video, i))
        super()._new_source(self.tracks)
