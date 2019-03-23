#!/usr/bin/env python

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets


class Audio(QtWidgets.QTabWidget):

    def __init__(self, parent, audio, index, codec, available_audio_encoders, outdex=None,
                 enabled=True, original=False, first=False, last=False, codecs=(), channels=2):
        super(Audio, self).__init__(parent)
        self.parent = parent
        self.audio = audio
        self.setFixedHeight(60)
        self.original = original
        self.outdex = index if self.original else outdex
        self.first = first
        self.last = last
        self.index = index
        self.codec = codec
        self.codecs = codecs
        self.channels = channels
        self.available_audio_encoders = available_audio_encoders

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f'{index}:{self.outdex}' if enabled else '❌'),
            audio_info=QtWidgets.QLineEdit(audio),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
            enable_check=QtWidgets.QCheckBox("Enabled"),
            dup_button=QtWidgets.QPushButton("➕"),
            delete_button=QtWidgets.QPushButton("⛔"),
            convert_to=None,
            convert_bitrate=None,
        )

        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(lambda: self.parent.reorder())

        self.widgets.dup_button.clicked.connect(lambda: self.dup_me())
        self.widgets.dup_button.setFixedWidth(20)
        self.widgets.delete_button.clicked.connect(lambda: self.del_me())
        self.widgets.delete_button.setFixedWidth(20)

        self.widgets.track_number.setFixedWidth(20)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.audio_info, 0, 2)
        grid.addLayout(self.init_conversion(), 0, 3)

        if not original:
            grid.addWidget(self.widgets.delete_button, 0, 4)
        else:
            grid.addWidget(self.widgets.dup_button, 0, 5)
            grid.addWidget(self.widgets.enable_check, 0, 4)
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
        self.update_codecs(self.codecs)

        self.widgets.convert_bitrate = QtWidgets.QComboBox()

        self.widgets.convert_bitrate.addItems([f'{x}k' for x in range(32 * self.channels,
                                                                      (256 * self.channels) + 1,
                                                                      32 * int(self.channels))])
        self.widgets.convert_bitrate.setCurrentIndex(3)

        layout.addWidget(QtWidgets.QLabel("Conversion: "))
        layout.addWidget(self.widgets.convert_to)

        layout.addWidget(QtWidgets.QLabel("Bitrate: "))
        layout.addWidget(self.widgets.convert_bitrate)

        return layout

    def update_codecs(self, codec_list):
        current = self.widgets.convert_to.currentText()
        for i in range(self.widgets.convert_to.count()):
            self.widgets.convert_to.removeItem(0)
        passthrough_available = False
        if self.codec in codec_list:
            passthrough_available = True
            self.widgets.convert_to.addItem('none')
        self.widgets.convert_to.addItems(sorted(set(self.available_audio_encoders) & set(codec_list)))
        if current in codec_list:
            index = codec_list.index(current)
            if passthrough_available:
                index += 1
            self.widgets.convert_to.setCurrentIndex(index)
        self.widgets.convert_to.setCurrentIndex(0)  # Will either go to 'copy' or first listed

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def conversion(self):
        return {'codec': self.widgets.convert_to.currentText(),
                'bitrate': self.widgets.convert_bitrate.currentText()}

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def dup_me(self):
        new = Audio(parent=self.parent, audio=self.audio, index=self.index,
                    outdex=len(self.parent.tracks) + 1, codec=self.codec,
                    available_audio_encoders=self.parent.available_audio_encoders,
                    enabled=True, original=False, codecs=self.codecs, channels=self.channels
                    )

        self.parent.tracks.append(new)
        self.parent.reorder()

    def del_me(self):
        self.parent.remove_track(self)

    def set_outdex(self, outdex):
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText('❌')
        else:
            self.widgets.track_number.setText(f'{self.index}:{self.outdex}')



class AudioList(QtWidgets.QWidget):

    def __init__(self, parent, available_audio_encoders):
        super(AudioList, self).__init__(parent)
        self.main = parent.main
        self.inner_layout = None
        self.available_audio_encoders = available_audio_encoders

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

    def new_source(self, codecs):
        self.inner_widget = QtWidgets.QWidget()
        self.tracks = []
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)

        for i, x in enumerate(self.main.streams.audio, 1):
            track_info = ""
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
                             codec=x.codec_name, codecs=codecs, channels=x.channels,
                             available_audio_encoders=self.available_audio_encoders)
            layout.addWidget(new_item)
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[-1].set_last()

        layout.addStretch()
        # layout.

        self.inner_layout = layout
        self.inner_widget.setLayout(layout)
        self.init_inner()

    def allowed_formats(self, allowed_formats=None):
        if not allowed_formats:
            return
        for track in self.tracks:
            track.update_codecs(allowed_formats)

    def reorder(self):
        for widget in self.tracks:
            self.inner_layout.removeWidget(widget)
        self.inner_layout.takeAt(0)
        disabled = 0
        for index, widget in enumerate(self.tracks, 1):
            self.inner_layout.addWidget(widget)
            if not widget.enabled:
                disabled += 1
            widget.set_outdex(index - disabled)
            widget.set_first(False)
            widget.set_last(False)
        self.tracks[0].set_first(True)
        self.tracks[-1].set_last(True)
        self.inner_layout.addStretch()
        self.inner_widget.setFixedHeight(len(self.tracks) * 70)
        self.inner_widget.setLayout(self.inner_layout)

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
                tracks.append({'index': track.index, 'outdex': track.outdex,
                               'conversion': track.conversion, 'codec': track.codec})
        print(tracks)
        return Box(audio_tracks=tracks)

    def remove_track(self, track):
        self.tracks.pop(self.tracks.index(track))
        track.close()
        self.reorder()
