#!/usr/bin/env python

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width


class Audio(QtWidgets.QTabWidget):

    def __init__(self, parent, audio, index, codec, enabled=True, original=False, first=False, last=False):
        super(Audio, self).__init__(parent)
        self.parent = parent
        self.audio = audio
        self.setFixedHeight(60)
        self.original = original
        self.first = first
        self.last = last
        self.index = index
        self.codec = codec

        self.widgets = Box(
            audio_info=QtWidgets.QLineEdit(audio),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
            enable_check=QtWidgets.QCheckBox("Enabled"),
            convert_to=None,
            convert_bitrate=None,
        )

        self.widgets.enable_check.setChecked(enabled)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.audio_info, 0, 1)
        grid.addLayout(self.init_conversion(), 0, 2)
        grid.addWidget(self.widgets.enable_check, 0, 3)
        self.setLayout(grid)

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

    def init_conversion(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()
        self.widgets.convert_to.addItems(['none',
                                          'libvorbis',
                                          'libopus'])

        self.widgets.convert_bitrate = QtWidgets.QComboBox()

        self.widgets.convert_bitrate.addItems(['96k'])

        layout.addWidget(QtWidgets.QLabel("Conversion: "))
        layout.addWidget(self.widgets.convert_to)

        layout.addWidget(QtWidgets.QLabel("Bitrate: "))
        layout.addWidget(self.widgets.convert_bitrate)

        return layout

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def conversion(self):
        if self.widgets.convert_bitrate.currentText() == 'none':
            return None
        return {'codec': self.widgets.convert_to.currentText(),
                'bitrate': self.widgets.convert_bitrate.currentText()}

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)


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
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)

        for i, x in enumerate(self.main.streams.audio, 1):
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

            new_item = Audio(self, track_info, original=True, first=True if i == 1 else False, index=x.index,
                             codec=x.codec_name)
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

    def get_settings(self):
        tracks = []
        for track in self.tracks:
            if track.enabled:
                tracks.append({'index': track.index, 'conversion': track.conversion, 'codec': track.codec})
        return Box(audio_tracks=tracks)
