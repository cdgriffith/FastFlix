#!/usr/bin/env python

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width



class Audio(QtWidgets.QTabWidget):

    def __init__(self, parent, audio, enabled=True, original=False, first=False, last=False):
        super(Audio, self).__init__(parent)
        self.parent = parent
        self.audio = audio
        self.widget = QtWidgets.QLineEdit()
        self.widget.setText(audio)
        self.widget.setDisabled(not enabled)
        self.setFixedHeight(60)
        self.original = original
        self.first = first
        self.last = last
        self.up_button = None
        self.down_button = None

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_buttons(), 0, 0)
        grid.addWidget(self.widget, 0, 1)
        self.setLayout(grid)

    def init_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        self.up_button = QtWidgets.QPushButton("^")
        self.up_button.setDisabled(self.first)
        self.up_button.setFixedWidth(20)
        self.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.down_button = QtWidgets.QPushButton("v")
        self.down_button.setDisabled(self.last)
        self.down_button.setFixedWidth(20)
        self.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.up_button)
        layout.addWidget(self.down_button)
        return layout

    def set_first(self, first=True):
        self.first = first
        self.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.down_button.setDisabled(self.last)


class AudioList(QtWidgets.QWidget):

    def __init__(self, parent):
        super(AudioList, self).__init__(parent)
        self.main = parent.main
        self.inner_layout = None

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel('Audio Tracks'))

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
        return super(AudioList, self).resizeEvent(event)

    def new_source(self):
        self.inner_widget = QtWidgets.QWidget()
        self.tracks = []
        text_audio_tracks = []
        for i, x in enumerate(self.main.streams.audio):
            track_info = f"{i}: "
            tags = x.get("tags")
            if tags:
                track_info += tags.get('title', '')
                if 'language' in tags:
                    track_info += f' {tags.language}'
            track_info += f' - {x.codec_name}'
            if 'profile' in x:
                track_info += f' ({x.profile})'
            track_info += f' - {x.channels} channels'

            text_audio_tracks.append(track_info)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)
        for index, track in enumerate(text_audio_tracks, 1):
            new_item = Audio(self, track, original=True, first=True if index == 1 else False)
            layout.addWidget(new_item)
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[-1].set_last()

        layout.addStretch()
        self.inner_layout = layout
        self.inner_widget.setLayout(layout)
        self.init_inner()

    def reorder(self):
        for widget in self.tracks:
            self.inner_layout.removeWidget(widget)
        for widget in self.tracks:
            self.inner_layout.addWidget(widget)
            widget.set_first(False)
            widget.set_last(False)
        self.tracks[0].set_first(True)
        self.tracks[-1].set_last(True)

    def move_up(self, audio_widget):
        index = self.tracks.index(audio_widget)
        self.tracks.insert(index - 1, self.tracks.pop(index))
        self.reorder()

    def move_down(self, audio_widget):
        index = self.tracks.index(audio_widget)
        self.tracks.insert(index + 1, self.tracks.pop(index))
        self.reorder()
