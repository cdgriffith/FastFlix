# -*- coding: utf-8 -*-
import gc

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp


class FlixList(QtWidgets.QWidget):
    """
    Children widgets must have "set_first", "set_last", and "set_outdex" methods and "enabled" property.
    """

    def __init__(self, app: FastFlixApp, parent, list_name, list_type, top_row_layout=None):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.setObjectName("FlixList")
        self.inner_layout = None
        self.list_type = list_type

        layout = QtWidgets.QVBoxLayout()
        if top_row_layout:
            layout.addLayout(top_row_layout)
        else:
            header_text = QtWidgets.QLabel(t(list_name))
            header_text.setFixedHeight(30)
            layout.addWidget(header_text)

        self.inner_widget = QtWidgets.QWidget()

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setMinimumHeight(200)

        layout.addWidget(self.scroll_area)
        self.tracks = []
        self.setLayout(layout)

    def init_inner(self):
        sp = QtWidgets.QSizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        self.inner_widget.setSizePolicy(sp)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super().resizeEvent(event)

    def _new_source(self, widgets):
        self.inner_widget.close()
        del self.inner_widget
        self.inner_widget = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)

        for widget in widgets:
            layout.addWidget(widget)

        layout.addStretch()
        self.inner_layout = layout
        self.inner_widget.setLayout(layout)
        self.init_inner()
        self.reorder()

    def new_source(self, *args, **kwargs):
        raise NotImplementedError()

    def reorder(self, update=True, height=66):
        if not self.inner_layout:
            return
        for widget in self.tracks:
            self.inner_layout.removeWidget(widget)
        self.inner_layout.takeAt(0)
        disabled = 0
        start = 1  # Audio starts after video
        if self.list_type == "subtitle":
            # After audio + video
            if (
                self.app.fastflix.current_video
                and self.app.fastflix.current_video.video_settings
                and isinstance(self.app.fastflix.current_video.audio_tracks, list)
            ):
                start = len([x for x in self.app.fastflix.current_video.audio_tracks if x.enabled]) + 1

        for index, widget in enumerate(self.tracks, start):
            self.inner_layout.addWidget(widget)
            if not widget.enabled:
                disabled += 1
            widget.set_outdex(index - disabled)
            widget.set_first(False)
            widget.set_last(False)
        if self.tracks:
            self.tracks[0].set_first(True)
            self.tracks[-1].set_last(True)
        self.inner_layout.addStretch()
        new_height = len(self.tracks) * height
        if len(self.tracks) <= 4:
            new_height += 30
        self.inner_widget.setFixedHeight(new_height)
        self.inner_widget.setLayout(self.inner_layout)
        if update:
            self.main.page_update(build_thumbnail=False)
        if self.app.fastflix.current_video:
            self.main.video_options.get_settings()

    def move_up(self, widget):
        index = self.tracks.index(widget)
        self.tracks.insert(index - 1, self.tracks.pop(index))
        self.reorder()

    def move_down(self, widget):
        index = self.tracks.index(widget)
        self.tracks.insert(index + 1, self.tracks.pop(index))
        self.reorder()

    def get_settings(self):
        raise NotImplementedError()

    def remove_track(self, track):
        del self.tracks[self.tracks.index(track)]
        track.close()
        del track
        self.reorder()
        gc.collect(2)

    def remove_all(self):
        for widget in self.tracks:
            self.inner_layout.removeWidget(widget)
            widget.close()
        self.tracks = []

    def __len__(self):
        return len([x for x in self.tracks if x.enabled])

    def refresh(self):
        self.reorder(update=False)
