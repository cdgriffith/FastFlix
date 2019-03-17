#!/usr/bin/env python

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width



class Audio(QtWidgets.QTabWidget):

    def __init__(self, parent, audio, number, enabled=True):
        super(Audio, self).__init__(parent)
        self.audio = audio
        self.widget = QtWidgets.QLineEdit()
        self.widget.setText(audio)
        self.widget.setDisabled(not enabled)
        self.setFixedHeight(60)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(f"Track {number}"), 0, 0, 1, 2)
        grid.addWidget(self.widget, 1, 0, 1, 2)
        self.setLayout(grid)


class AudioList(QtWidgets.QWidget):

    def __init__(self, parent):
        super(AudioList, self).__init__(parent)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel('Audio Tracks'))

        self.inner_widget = QtWidgets.QWidget()

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setMinimumHeight(300)

        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def update_audio(self, audio_tracks):
        self.inner_widget = QtWidgets.QWidget()
        sp = QtWidgets.QSizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        self.inner_widget.setSizePolicy(sp)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)
        for index, track in enumerate(audio_tracks, 1):
            new_item = Audio(self.scroll_area, track, index)
            layout.addWidget(new_item)
        layout.addStretch()
        self.inner_widget.setLayout(layout)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super(AudioList, self).resizeEvent(event)
