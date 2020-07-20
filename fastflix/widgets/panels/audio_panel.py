#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box

from fastflix.shared import QtGui, QtCore, QtWidgets
from fastflix.widgets.panels.abstract_list import FlixList


class Audio(QtWidgets.QTabWidget):
    def __init__(
        self,
        parent,
        audio,
        index,
        codec,
        available_audio_encoders,
        title="",
        language="",
        profile="",
        outdex=None,
        enabled=True,
        original=False,
        first=False,
        last=False,
        codecs=(),
        channels=2,
    ):
        self.loading = True
        super(Audio, self).__init__(parent)
        self.parent = parent
        self.audio = audio
        self.setFixedHeight(60)
        self.original = original
        self.outdex = index if self.original else outdex
        self.first = first
        self.track_name = title
        self.profile = profile
        self.language = language
        self.last = last
        self.index = index
        self.codec = codec
        self.codecs = codecs
        self.channels = channels
        self.available_audio_encoders = available_audio_encoders

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLineEdit(title),
            audio_info=QtWidgets.QLabel(audio),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
            enable_check=QtWidgets.QCheckBox("Enabled"),
            dup_button=QtWidgets.QPushButton("➕"),
            delete_button=QtWidgets.QPushButton("⛔"),
            downmix=QtWidgets.QComboBox(),
            convert_to=None,
            convert_bitrate=None,
        )

        downmix_options = [
            "mono",
            "stereo",
            "2.1 / 3.0",
            "3.1 / 4.0",
            "4.1 / 5.0",
            "5.1 / 6.0",
            "6.1 / 7.0",
            "7.1 / 8.0",
        ]
        self.widgets.title.setFixedWidth(200)
        self.widgets.audio_info.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.widgets.downmix.addItems(["No Downmix"] + downmix_options[: channels - 2])
        self.widgets.downmix.currentIndexChanged.connect(self.update_downmix)
        self.widgets.downmix.setCurrentIndex(0)
        self.widgets.downmix.setDisabled(True)

        self.widgets.enable_check
        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)

        self.widgets.dup_button.clicked.connect(lambda: self.dup_me())
        self.widgets.dup_button.setFixedWidth(20)
        self.widgets.delete_button.clicked.connect(lambda: self.del_me())
        self.widgets.delete_button.setFixedWidth(20)

        self.widgets.track_number.setFixedWidth(20)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.audio_info, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Title: "), 0, 3)
        grid.addWidget(self.widgets.title, 0, 4)
        grid.addLayout(self.init_conversion(), 0, 5)
        grid.addWidget(self.widgets.downmix, 0, 6)

        if not original:
            spacer = QtWidgets.QLabel()
            spacer.setFixedWidth(63)
            grid.addWidget(spacer, 0, 7)
            grid.addWidget(self.widgets.delete_button, 0, 8)
        else:
            grid.addWidget(self.widgets.enable_check, 0, 7)
            grid.addWidget(self.widgets.dup_button, 0, 8)
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

    def init_conversion(self):
        layout = QtWidgets.QHBoxLayout()
        self.widgets.convert_to = QtWidgets.QComboBox()

        self.update_codecs(self.codecs)

        self.widgets.convert_bitrate = QtWidgets.QComboBox()
        self.widgets.convert_bitrate.setFixedWidth(70)

        self.widgets.convert_bitrate.addItems(
            [f"{x}k" for x in range(32 * self.channels, (256 * self.channels) + 1, 32 * self.channels)]
        )
        self.widgets.convert_bitrate.setCurrentIndex(3)

        self.widgets.convert_bitrate.currentIndexChanged.connect(lambda: self.page_update())
        self.widgets.convert_to.currentIndexChanged.connect(self.update_conversion)
        layout.addWidget(QtWidgets.QLabel("Conversion: "))
        layout.addWidget(self.widgets.convert_to)

        layout.addWidget(QtWidgets.QLabel("Bitrate: "))
        layout.addWidget(self.widgets.convert_bitrate)

        return layout

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        self.widgets.track_number.setText(f"{self.index}:{self.outdex}" if enabled else "❌")
        self.parent.reorder()
        self.page_update()

    def update_downmix(self):
        channels = self.widgets.downmix.currentIndex()
        self.widgets.convert_bitrate.clear()
        if channels > 0:
            self.widgets.convert_bitrate.addItems(
                [f"{x}k" for x in range(32 * channels, (256 * channels) + 1, 32 * channels)]
            )
        else:
            self.widgets.convert_bitrate.addItems(
                [f"{x}k" for x in range(32 * self.channels, (256 * self.channels) + 1, 32 * self.channels)]
            )
        self.widgets.convert_bitrate.setCurrentIndex(3)
        self.page_update()

    def update_conversion(self):
        if self.widgets.convert_to.currentIndex() == 0:
            self.widgets.downmix.setDisabled(True)
        else:
            self.widgets.downmix.setDisabled(False)
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update()

    def update_codecs(self, codec_list):
        self.loading = True
        current = self.widgets.convert_to.currentText()
        self.widgets.convert_to.clear()
        # passthrough_available = False
        # if self.codec in codec_list:
        passthrough_available = True
        self.widgets.convert_to.addItem("none")
        self.widgets.convert_to.addItems(sorted(set(self.available_audio_encoders) & set(codec_list)))
        if current in codec_list:
            index = codec_list.index(current)
            if passthrough_available:
                index += 1
            self.widgets.convert_to.setCurrentIndex(index)
        self.widgets.convert_to.setCurrentIndex(0)  # Will either go to 'copy' or first listed
        self.loading = False

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def conversion(self):
        return {"codec": self.widgets.convert_to.currentText(), "bitrate": self.widgets.convert_bitrate.currentText()}

    @property
    def downmix(self):
        return self.widgets.downmix.currentIndex()

    @property
    def title(self):
        return self.widgets.title.text()

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def dup_me(self):
        new = Audio(
            parent=self.parent,
            audio=self.audio,
            index=self.index,
            outdex=len(self.parent.tracks) + 1,
            codec=self.codec,
            available_audio_encoders=self.available_audio_encoders,
            enabled=True,
            original=False,
            codecs=self.codecs,
            channels=self.channels,
        )

        self.parent.tracks.append(new)
        self.parent.reorder()

    def del_me(self):
        self.parent.remove_track(self)

    def set_outdex(self, outdex):
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{self.index}:{self.outdex}")


class AudioList(FlixList):
    def __init__(self, parent, available_audio_encoders, starting_pos=0):
        super(AudioList, self).__init__(parent, "Audio Tracks", starting_pos)
        self.available_audio_encoders = available_audio_encoders

    def new_source(self, codecs, starting_pos=0):
        self.starting_pos = starting_pos
        self.tracks = []
        for i, x in enumerate(self.main.streams.audio):
            track_info = ""
            tags = x.get("tags", {})
            if tags:
                track_info += tags.get("title", "")
                if "language" in tags:
                    track_info += f" {tags.language}"
            track_info += f" - {x.codec_name}"
            if "profile" in x:
                track_info += f" ({x.profile})"
            track_info += f" - {x.channels} channels"

            new_item = Audio(
                self,
                track_info,
                title=tags.get("title"),
                language=tags.get("language"),
                profile=x.get("profile"),
                original=True,
                first=True if i == 0 else False,
                index=x.index,
                codec=x.codec_name,
                codecs=codecs,
                channels=x.channels,
                available_audio_encoders=self.available_audio_encoders,
            )
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        super()._new_source(self.tracks)

    def allowed_formats(self, allowed_formats=None):
        if not allowed_formats:
            return
        for track in self.tracks:
            track.update_codecs(allowed_formats)

    def get_settings(self):
        tracks = []
        for track in self.tracks:
            if track.enabled:
                tracks.append(
                    {
                        "index": track.index,
                        "outdex": track.outdex,
                        "conversion": track.conversion,
                        "codec": track.codec,
                        "downmix": track.downmix,
                        "title": track.title,
                    }
                )
        return Box(audio_tracks=tracks)
