#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width
from flix.widgets.panels.abstract_list import FlixList

dispositions = [
    "none",
    "default",
    "dub",
    "original",
    "comment",
    "lyrics",
    "karaoke",
    "forced",
    "hearing_impaired",
    "visual_impaired",
    "clean_effects",
    "attached_pic",
    "timed_thumbnails",
]


class Subtitle(QtWidgets.QTabWidget):
    def __init__(self, parent, subtitle, index, enabled=True, first=False):
        self.loading = True
        super(Subtitle, self).__init__(parent)
        self.parent = parent
        self.index = index
        self.outdex = None
        self.subtitle = Box(subtitle, default_box=True)
        self.first = first
        self.last = False

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{self.index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLabel(f"{self.subtitle.codec_long_name} {self.subtitle.tags.get('language')}"),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
            enable_check=QtWidgets.QCheckBox("Preserve"),
            disposition=QtWidgets.QComboBox()
            # dup_button=QtWidgets.QPushButton("➕"),
            # delete_button=QtWidgets.QPushButton("⛔"),
            # downmix=QtWidgets.QComboBox(),
            # convert_to=None,
            # convert_bitrate=None,
        )

        self.widgets.disposition.addItems(dispositions)
        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)
        self.widgets.disposition.currentIndexChanged.connect(self.page_update)
        self.widgets.disposition.setCurrentIndex(0)
        for disposition, is_set in self.subtitle.disposition.items():
            if is_set:
                try:
                    self.widgets.downmix.setCurrentIndex(dispositions.index(disposition))
                except ValueError:
                    pass  # TODO figure out all possible dispositions for subtitles / log if issue
                break

        self.setFixedHeight(60)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.title, 0, 2)
        grid.addWidget(self.widgets.enable_check, 0, 3)
        grid.addWidget(QtWidgets.QLabel("Disposition"), 0, 4)
        grid.addWidget(self.widgets.disposition, 0, 5)

        self.setLayout(grid)
        self.loading = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        # self.widgets.up_button = QtWidgets.QPushButton("^")
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        # self.widgets.down_button = QtWidgets.QPushButton("v")
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
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{self.index}:{self.outdex}")

    @property
    def disposition(self):
        text = self.widgets.disposition.currentText()
        return 0 if text == "none" else text

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        self.widgets.track_number.setText(f"{self.index}:{self.outdex}" if enabled else "❌")
        self.parent.reorder()
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update()


class SubtitleList(FlixList):
    def __init__(self, parent, starting_pos=0):
        super().__init__(parent, "Subtitle Tracks", starting_pos)
        self.main = parent.main

    def new_source(self, starting_pos=0):
        self.starting_pos = starting_pos
        self.tracks = []
        for index, track in enumerate(self.main.streams.subtitle):
            new_item = Subtitle(self, track, index=track.index, first=True if index == 0 else False)
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[-1].set_last()

        super()._new_source(self.tracks)

    def get_settings(self):
        tracks = []
        for track in self.tracks:
            if track.enabled:
                tracks.append({"index": track.index, "outdex": track.outdex, "disposition": track.disposition})
        return Box(subtitle_tracks=tracks)
