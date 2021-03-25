#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import List, Optional

from box import Box
from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.audio import lossless, channel_list
from fastflix.language import t
from fastflix.models.encode import AudioTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import black_x_icon, copy_icon, down_arrow_icon, up_arrow_icon
from fastflix.shared import no_border, error_message
from fastflix.widgets.panels.abstract_list import FlixList

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())


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
        all_info=None,
        disable_dup=False,
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
        self.last = last
        self.index = index
        self.codec = codec
        self.codecs = codecs
        self.channels = channels
        self.available_audio_encoders = available_audio_encoders
        self.all_info = all_info

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLineEdit(title),
            audio_info=QtWidgets.QLabel(audio),
            up_button=QtWidgets.QPushButton(QtGui.QIcon(up_arrow_icon), ""),
            down_button=QtWidgets.QPushButton(QtGui.QIcon(down_arrow_icon), ""),
            enable_check=QtWidgets.QCheckBox(t("Enabled")),
            dup_button=QtWidgets.QPushButton(QtGui.QIcon(copy_icon), ""),
            delete_button=QtWidgets.QPushButton(QtGui.QIcon(black_x_icon), ""),
            language=QtWidgets.QComboBox(),
            downmix=QtWidgets.QComboBox(),
            convert_to=None,
            convert_bitrate=None,
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)
        self.widgets.dup_button.setStyleSheet(no_border)
        self.widgets.delete_button.setStyleSheet(no_border)

        if all_info:
            self.widgets.audio_info.setToolTip(all_info.to_yaml())

        self.widgets.language.addItems(["No Language Set"] + language_list)
        self.widgets.language.setMaximumWidth(110)
        if language:
            try:
                lang = Lang(language).name
            except InvalidLanguageValue:
                pass
            else:
                if lang in language_list:
                    self.widgets.language.setCurrentText(lang)

        self.widgets.language.currentIndexChanged.connect(self.page_update)
        self.widgets.title.setFixedWidth(150)
        self.widgets.title.textChanged.connect(self.page_update)
        self.widgets.audio_info.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.widgets.downmix.addItems([t("No Downmix")] + [k for k, v in channel_list.items() if v <= channels])
        self.widgets.downmix.currentIndexChanged.connect(self.update_downmix)
        self.widgets.downmix.setCurrentIndex(0)
        self.widgets.downmix.setDisabled(True)

        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)

        self.widgets.dup_button.clicked.connect(lambda: self.dup_me())
        self.widgets.dup_button.setFixedWidth(20)
        if disable_dup:
            self.widgets.dup_button.hide()
            self.widgets.dup_button.setDisabled(True)

        self.widgets.delete_button.clicked.connect(lambda: self.del_me())
        self.widgets.delete_button.setFixedWidth(20)

        self.widgets.track_number.setFixedWidth(20)

        label = QtWidgets.QLabel(f"{t('Title')}: ")
        self.widgets.title.setFixedWidth(150)
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.addWidget(label)
        title_layout.addWidget(self.widgets.title)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.audio_info, 0, 2)
        grid.addLayout(title_layout, 0, 3)
        # grid.addWidget(self.widgets.title, 0, 4)
        grid.addLayout(self.init_conversion(), 0, 5)
        grid.addWidget(self.widgets.downmix, 0, 6)
        grid.addWidget(self.widgets.language, 0, 7)

        right_button_start_index = 8

        if not original:
            spacer = QtWidgets.QLabel()
            spacer.setFixedWidth(63)
            grid.addWidget(spacer, 0, right_button_start_index)
            grid.addWidget(self.widgets.delete_button, 0, right_button_start_index + 1)
        else:
            grid.addWidget(self.widgets.enable_check, 0, right_button_start_index)
            grid.addWidget(self.widgets.dup_button, 0, right_button_start_index + 1)
        self.setLayout(grid)
        self.loading = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        # layout.setMargin(0)
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
            [f"{x}k" for x in range(16 * self.channels, (256 * self.channels) + 1, 16 * self.channels)]
            if self.channels
            else [
                "32k",
                "64k",
                "96k",
                "128k",
                "160k",
                "192k",
                "224k",
                "256k",
                "320k",
                "512K",
                "768k",
                "896k",
                "1024k",
                "1152k",
                "1280k",
                "1408k",
                "1536k",
                "1664k",
                "1792k",
                "1920k",
            ]
        )
        self.widgets.convert_bitrate.setCurrentIndex(3)
        self.widgets.convert_bitrate.setDisabled(True)

        self.widgets.convert_bitrate.currentIndexChanged.connect(lambda: self.page_update())
        self.widgets.convert_to.currentIndexChanged.connect(self.update_conversion)
        layout.addWidget(QtWidgets.QLabel(f"{t('Conversion')}: "))
        layout.addWidget(self.widgets.convert_to)

        layout.addWidget(QtWidgets.QLabel(f"{t('Bitrate')}: "))
        layout.addWidget(self.widgets.convert_bitrate)

        return layout

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        self.widgets.track_number.setText(f"{self.index}:{self.outdex}" if enabled else "❌")
        self.parent.reorder(update=True)

    def update_downmix(self):
        channels = (
            channel_list[self.widgets.downmix.currentText()]
            if self.widgets.downmix.currentIndex() > 0
            else self.channels
        )
        self.widgets.convert_bitrate.clear()
        if channels > 0:
            self.widgets.convert_bitrate.addItems(
                [f"{x}k" for x in range(16 * channels, (256 * channels) + 1, 16 * channels)]
            )
        else:
            self.widgets.convert_bitrate.addItems(
                [f"{x}k" for x in range(16 * self.channels, (256 * self.channels) + 1, 16 * self.channels)]
            )
        self.widgets.convert_bitrate.setCurrentIndex(3)
        self.page_update()

    def update_conversion(self):
        if self.widgets.convert_to.currentIndex() == 0:
            self.widgets.downmix.setDisabled(True)
            self.widgets.convert_bitrate.setDisabled(True)
        else:
            self.widgets.downmix.setDisabled(False)
            if self.widgets.convert_to.currentText() in lossless:
                self.widgets.convert_bitrate.setDisabled(True)
            else:
                self.widgets.convert_bitrate.setDisabled(False)
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)

    def update_codecs(self, codec_list):
        self.loading = True
        current = self.widgets.convert_to.currentText()
        self.widgets.convert_to.clear()
        # passthrough_available = False
        # if self.codec in codec_list:
        passthrough_available = True
        self.widgets.convert_to.addItem(t("none"))
        self.widgets.convert_to.addItems(sorted(set(self.available_audio_encoders) & set(codec_list)))
        if current in codec_list:
            index = codec_list.index(current)
            if passthrough_available:
                index += 1
            self.widgets.convert_to.setCurrentIndex(index)
        self.widgets.convert_to.setCurrentIndex(0)  # Will either go to 'copy' or first listed
        if self.widgets.convert_bitrate:
            self.widgets.convert_bitrate.setDisabled(True)
        self.loading = False

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def conversion(self):
        if self.widgets.convert_to.currentIndex() == 0:
            return {"codec": "", "bitrate": ""}
        return {"codec": self.widgets.convert_to.currentText(), "bitrate": self.widgets.convert_bitrate.currentText()}

    @property
    def downmix(self) -> Optional[str]:
        return self.widgets.downmix.currentText() if self.widgets.downmix.currentIndex() > 0 else None

    @property
    def language(self) -> str:
        if self.widgets.language.currentIndex() == 0:
            return ""
        return Lang(self.widgets.language.currentText()).pt2b

    @property
    def title(self) -> str:
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
            language=self.language,
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
    def __init__(self, parent, app: FastFlixApp):
        super(AudioList, self).__init__(app, parent, t("Audio Tracks"), "audio")
        self.available_audio_encoders = app.fastflix.audio_encoders
        self.app = app
        self._first_selected = False

    def lang_match(self, track):
        if not self.app.fastflix.config.opt("audio_select"):
            return False
        if not self.app.fastflix.config.opt("audio_select_preferred_language"):
            if self.app.fastflix.config.opt("audio_select_first_matching") and self._first_selected:
                return False
            self._first_selected = True
            return True
        try:
            track_lang = Lang(track.get("tags", {}).get("language", ""))
        except InvalidLanguageValue:
            return True
        else:
            if Lang(self.app.fastflix.config.opt("audio_language")) == track_lang:
                if self.app.fastflix.config.opt("audio_select_first_matching") and self._first_selected:
                    return False
                self._first_selected = True
                return True
        return False

    def new_source(self, codecs):
        self.tracks: List[Audio] = []
        self._first_selected = False
        disable_dup = "nvencc" in self.main.convert_to.lower()
        for i, x in enumerate(self.app.fastflix.current_video.streams.audio, start=1):
            track_info = ""
            tags = x.get("tags", {})
            if tags:
                track_info += tags.get("title", "")
                # if "language" in tags:
                #     track_info += f" {tags.language}"
            track_info += f" - {x.codec_name}"
            if "profile" in x:
                track_info += f" ({x.profile})"
            track_info += f" - {x.channels} {t('channels')}"

            new_item = Audio(
                self,
                track_info,
                title=tags.get("title"),
                language=tags.get("language"),
                profile=x.get("profile"),
                original=True,
                first=True if i == 0 else False,
                index=x.index,
                outdex=i,
                codec=x.codec_name,
                codecs=codecs,
                channels=x.channels,
                available_audio_encoders=self.available_audio_encoders,
                enabled=self.lang_match(x),
                all_info=x,
                disable_dup=disable_dup,
            )
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        super()._new_source(self.tracks)
        self.update_audio_settings()

    def allowed_formats(self, allowed_formats=None):
        disable_dups = "nvencc" in self.main.convert_to.lower()
        tracks_need_removed = False
        for track in self.tracks:
            track.widgets.dup_button.setDisabled(disable_dups)
            if not track.original:
                if disable_dups:
                    tracks_need_removed = True
            else:
                if disable_dups:
                    track.widgets.dup_button.hide()
                else:
                    track.widgets.dup_button.show()
        if tracks_need_removed:
            error_message(t("This encoder does not support duplicating audio tracks, please remove copied tracks!"))
        if not allowed_formats:
            return
        for track in self.tracks:
            track.update_codecs(allowed_formats or set())

    def update_audio_settings(self):
        tracks = []
        for track in self.tracks:
            if track.enabled:
                tracks.append(
                    AudioTrack(
                        index=track.index,
                        outdex=track.outdex,
                        conversion_bitrate=track.conversion["bitrate"],
                        conversion_codec=track.conversion["codec"],
                        codec=track.codec,
                        downmix=track.downmix,
                        title=track.title,
                        language=track.language,
                        profile=track.profile,
                        channels=track.channels,
                        enabled=track.enabled,
                        original=track.original,
                        raw_info=track.all_info,
                        friendly_info=track.audio,
                    )
                )
        self.app.fastflix.current_video.video_settings.audio_tracks = tracks

    def reload(self, original_tracks: List[AudioTrack], audio_formats):
        disable_dups = "nvencc" in self.main.convert_to.lower()

        repopulated_tracks = set()
        for track in original_tracks:
            if track.original:
                repopulated_tracks.add(track.index)

            new_track = Audio(
                parent=self,
                audio=track.friendly_info,
                all_info=Box(track.raw_info) if track.raw_info else None,
                title=track.title,
                language=track.language,
                profile=track.profile,
                original=track.original,
                index=track.index,
                outdex=track.outdex,
                codec=track.codec,
                codecs=audio_formats,
                channels=track.channels,
                available_audio_encoders=self.available_audio_encoders,
                enabled=True,
                disable_dup=disable_dups,
            )

            new_track.widgets.downmix.setCurrentText(track.downmix)
            new_track.widgets.convert_to.setCurrentText(track.conversion_codec)
            new_track.widgets.convert_bitrate.setCurrentText(track.conversion_bitrate)
            new_track.widgets.title.setText(track.title)
            if track.language:
                new_track.widgets.language.setCurrentText(Lang(track.language).name)
            else:
                new_track.widgets.language.setCurrentIndex(0)

            self.tracks.append(new_track)

        for i, x in enumerate(self.app.fastflix.current_video.streams.audio, start=1):
            if x.index in repopulated_tracks:
                continue
            track_info = ""
            tags = x.get("tags", {})
            if tags:
                track_info += tags.get("title", "")
                # if "language" in tags:
                #     track_info += f" {tags.language}"
            track_info += f" - {x.codec_name}"
            if "profile" in x:
                track_info += f" ({x.profile})"
            track_info += f" - {x.channels} {t('channels')}"

            new_item = Audio(
                self,
                track_info,
                title=tags.get("title"),
                language=tags.get("language"),
                profile=x.get("profile"),
                original=True,
                index=x.index,
                outdex=i,
                codec=x.codec_name,
                codecs=audio_formats,
                channels=x.channels,
                available_audio_encoders=self.available_audio_encoders,
                enabled=False,
                all_info=x,
                disable_dup=disable_dups,
            )
            self.tracks.append(new_item)

        self.tracks.sort(key=lambda z: (int(not z.original), z.index))

        super()._new_source(self.tracks)
