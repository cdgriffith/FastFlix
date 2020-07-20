# -*- coding: utf-8 -*-
from box import Box

from fastflix.shared import QtGui, QtCore, QtWidgets


class FlixList(QtWidgets.QWidget):
    """
    Children widgets must have "set_first", "set_last", and "set_outdex" methods and "enabled" property.
    """

    def __init__(self, parent, list_name, starting_pos=1):
        super().__init__(parent)
        self.main = parent.main
        self.inner_layout = None
        self.starting_pos = starting_pos

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel(list_name))

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

    def reorder(self, update=True):
        for widget in self.tracks:
            self.inner_layout.removeWidget(widget)
        self.inner_layout.takeAt(0)
        disabled = 0
        for index, widget in enumerate(self.tracks, self.starting_pos):
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
        self.inner_widget.setFixedHeight(len(self.tracks) * 70)
        self.inner_widget.setLayout(self.inner_layout)
        if update:
            self.main.page_update()

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
        self.tracks.pop(self.tracks.index(track))
        track.close()
        self.reorder()

    def __len__(self):
        return len([x for x in self.tracks if x.enabled])

    def refresh(self, starting_pos=0):
        self.starting_pos = starting_pos
        self.reorder(update=False)
