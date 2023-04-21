#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional
import logging

from box import Box
from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.audio import lossless, channel_list
from fastflix.language import t
from fastflix.models.encode import AudioTrack
from fastflix.models.profiles import Profile
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon
from fastflix.shared import no_border, error_message, yes_no_message
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.audio_processing import apply_audio_filters
from fastflix.widgets.windows.disposition import Disposition

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())
logger = logging.getLogger("fastflix")

disposition_options = [
    "default",
    "dub",
    "original",
    "comment",
    "lyrics",
    "karaoke",
    "forced",
    "visual_impaired",
    "clean_effects",
    "captions",
    "descriptions",
    "dependent",
    "metadata",
]


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
        dispositions=None,
    ):
        self.loading = True
        super(Audio, self).__init__(parent)
        self.setObjectName("Audio")
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
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            enable_check=QtWidgets.QCheckBox(t("Enabled")),
            dup_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("onyx-copy", self.parent.app.fastflix.config.theme)), ""
            ),
            delete_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("black-x", self.parent.app.fastflix.config.theme)), ""
            ),
            language=QtWidgets.QComboBox(),
            downmix=QtWidgets.QComboBox(),
            convert_to=None,
            convert_bitrate=None,
            disposition=QtWidgets.QPushButton(),
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)
        self.widgets.dup_button.setStyleSheet(no_border)
        self.widgets.delete_button.setStyleSheet(no_border)

        if all_info:
            self.widgets.audio_info.setToolTip(all_info.to_yaml())

        self.widgets.language.addItems(["No Language Set"] + language_list)
        self.widgets.language.setMaximumWidth(150)
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
        # self.widgets.audio_info.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.widgets.audio_info.setFixedWidth(350)
        self.widgets.downmix.addItems([t("No Downmix")] + [k for k, v in channel_list.items() if v <= channels])
        self.widgets.downmix.currentIndexChanged.connect(self.update_downmix)
        self.widgets.downmix.setCurrentIndex(0)
        self.widgets.downmix.setDisabled(True)
        self.widgets.downmix.hide()

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

        self.dispositions = dispositions or {k: False for k in disposition_options}

        self.disposition_widget = Disposition(self, f"Audio Track {index}", subs=True)
        self.set_dis_button()
        self.widgets.disposition.clicked.connect(self.disposition_widget.show)

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addWidget(QtWidgets.QLabel(t("Dispositions")))
        disposition_layout.addWidget(self.widgets.disposition)

        label = QtWidgets.QLabel(f"{t('Title')}: ")
        self.widgets.title.setFixedWidth(150)
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.addStretch(False)
        title_layout.addWidget(label, stretch=False)
        title_layout.addWidget(self.widgets.title, stretch=False)
        title_layout.addStretch(True)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.audio_info, 0, 2)
        grid.addLayout(title_layout, 0, 3)
        grid.addLayout(disposition_layout, 0, 4)
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
        self.widgets.convert_bitrate.addItems(self.get_conversion_bitrates())
        self.widgets.convert_bitrate.setCurrentIndex(3)
        self.widgets.convert_bitrate.setDisabled(True)
        self.widgets.bitrate_label = QtWidgets.QLabel(f"{t('Bitrate')}: ")
        self.widgets.convert_bitrate.hide()
        self.widgets.bitrate_label.hide()

        self.widgets.convert_bitrate.currentIndexChanged.connect(lambda: self.page_update())
        self.widgets.convert_to.currentIndexChanged.connect(self.update_conversion)
        layout.addWidget(QtWidgets.QLabel(f"{t('Conversion')}: "))
        layout.addWidget(self.widgets.convert_to)

        layout.addWidget(self.widgets.bitrate_label)
        layout.addWidget(self.widgets.convert_bitrate)

        return layout

    def set_dis_button(self):
        output = ""
        for disposition, is_set in self.dispositions.items():
            if is_set:
                output += f"{t(disposition)},"
        if output:
            self.widgets.disposition.setText(output.rstrip(","))
        else:
            self.widgets.disposition.setText(t("none"))

    def get_conversion_bitrates(self, channels=None):
        if not channels:
            channels = self.channels or 2
        bitrates = [x for x in range(16 * channels, (256 * channels) + 1, 16 * channels)]
        if channels > 1:
            bitrates.append(640)
        return [f"{x}k" for x in sorted(set(bitrates))]

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
        if self.conversion["codec"] not in lossless:
            self.widgets.convert_bitrate.clear()
            self.widgets.convert_bitrate.addItems(self.get_conversion_bitrates(channels))
            self.widgets.convert_bitrate.setCurrentIndex(3)
        self.page_update()

    def update_conversion(self):
        if self.widgets.convert_to.currentIndex() == 0:
            self.widgets.downmix.setDisabled(True)
            self.widgets.convert_bitrate.setDisabled(True)
            self.widgets.convert_bitrate.hide()
            self.widgets.bitrate_label.hide()
            self.widgets.downmix.hide()
        else:
            self.widgets.downmix.setDisabled(False)
            self.widgets.convert_bitrate.show()
            self.widgets.bitrate_label.show()
            self.widgets.downmix.show()
            if self.conversion["codec"] in lossless:
                self.widgets.convert_bitrate.setDisabled(True)
                self.widgets.convert_bitrate.addItem("lossless")
                self.widgets.convert_bitrate.setCurrentText("lossless")
            else:
                self.widgets.convert_bitrate.setDisabled(False)
                self.widgets.convert_bitrate.clear()
                channels = (
                    channel_list[self.widgets.downmix.currentText()]
                    if self.widgets.downmix.currentIndex() > 0
                    else self.channels
                )
                self.widgets.convert_bitrate.addItems(self.get_conversion_bitrates(channels))
                self.widgets.convert_bitrate.setCurrentIndex(3)
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
            dispositions=self.dispositions,
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
        super(AudioList, self).__init__(app, parent, "Audio Tracks", "audio")
        self.available_audio_encoders = app.fastflix.audio_encoders
        self.app = app
        self._first_selected = False

    def _get_track_info(self, track):
        track_info = ""
        tags = track.get("tags", {})
        if tags:
            track_info += tags.get("title", "")
            # if "language" in tags:
            #     track_info += f" {tags.language}"
        track_info += f" - {track.codec_name}"
        if "profile" in track:
            track_info += f" ({track.profile})"
        track_info += f" - {track.channels} {t('channels')}"
        return track_info, tags

    def enable_all(self):
        for track in self.tracks:
            track.widgets.enable_check.setChecked(True)

    def disable_all(self):
        for track in self.tracks:
            track.widgets.enable_check.setChecked(False)

    def new_source(self, codecs):
        self.tracks: list[Audio] = []
        self._first_selected = False
        disable_dup = (
            "nvencc" in self.main.convert_to.lower()
            or "vcenc" in self.main.convert_to.lower()
            or "qsvenc" in self.main.convert_to.lower()
        )
        for i, x in enumerate(self.app.fastflix.current_video.streams.audio, start=1):
            track_info, tags = self._get_track_info(x)
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
                enabled=True,
                all_info=x,
                disable_dup=disable_dup,
                dispositions={k: bool(v) for k, v in x.disposition.items()},
            )
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()
        super()._new_source(self.tracks)
        self.update_audio_settings()

    def allowed_formats(self, allowed_formats=None):
        disable_dups = (
            "nvencc" in self.main.convert_to.lower()
            or "vcenc" in self.main.convert_to.lower()
            or "qsvenc" in self.main.convert_to.lower()
        )
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

    def apply_profile_settings(
        self,
        profile: Profile,
        original_tracks: list[Box],
        audio_formats,
        og_only: bool = False,
    ):
        if isinstance(profile.audio_filters, list) or profile.audio_filters is False:
            self.disable_all()
        else:
            self.enable_all()
            return

        self.tracks = []

        def update_track(new_track, downmix=None, conversion=None, bitrate=None):
            if conversion:
                new_track.widgets.convert_to.setCurrentText(conversion)
                # Downmix must come first
                if downmix:
                    new_track.widgets.downmix.setCurrentText(downmix)
                if conversion in lossless:
                    new_track.widgets.convert_bitrate.setDisabled(True)
                    new_track.widgets.convert_bitrate.addItem("lossless")
                    new_track.widgets.convert_bitrate.setCurrentText("lossless")
                else:
                    if bitrate not in [
                        new_track.widgets.convert_bitrate.itemText(i)
                        for i in range(new_track.widgets.convert_bitrate.count())
                    ]:
                        new_track.widgets.convert_bitrate.addItem(bitrate)
                    new_track.widgets.convert_bitrate.setCurrentText(bitrate)
                    new_track.widgets.convert_bitrate.setDisabled(False)

        def gen_track(
            parent, audio_track, outdex, og=False, enabled=True, downmix=None, conversion=None, bitrate=None
        ) -> Audio:
            track_info, tags = self._get_track_info(audio_track)
            new_track = Audio(
                parent,
                track_info,
                title=tags.get("title"),
                language=tags.get("language"),
                profile=audio_track.get("profile"),
                original=og,
                index=audio_track.index,
                outdex=outdex,
                codec=audio_track.codec_name,
                codecs=audio_formats,
                channels=audio_track.channels,
                available_audio_encoders=self.available_audio_encoders,
                enabled=enabled,
                all_info=audio_track,
                disable_dup=og_only,
            )

            update_track(new_track=new_track, downmix=downmix, conversion=conversion, bitrate=bitrate)

            return new_track

        # First populate all original tracks and disable them
        for i, track in enumerate(original_tracks, start=1):
            self.tracks.append(gen_track(self, track, outdex=i, og=True, enabled=False))

        tracks = apply_audio_filters(profile.audio_filters, original_tracks=original_tracks)

        if profile.audio_filters is not False and self.tracks and not tracks:
            enable = yes_no_message(
                t("No audio tracks matched for this profile, enable first track?"), title="No Audio Match"
            )
            if enable:
                self.tracks[0].widgets.enable_check.setChecked(True)
            return super()._new_source(self.tracks)

        # Apply first set of conversions to the original audio tracks
        current_id = -1
        skip_tracks = []
        for idx, track in enumerate(tracks):
            # track[0] is the Box() track object, track[1] is the AudioMatch it matched against
            if track[0].index > current_id:
                current_id = track[0].index
                self.tracks[track[0].index - 1].widgets.enable_check.setChecked(True)
                update_track(
                    self.tracks[track[0].index - 1],
                    downmix=track[1].downmix,
                    conversion=track[1].conversion,
                    bitrate=track[1].bitrate,
                )
                skip_tracks.append(idx)

        if not og_only:
            additional_tracks = []
            for i, track in enumerate(tracks):
                if i not in skip_tracks:
                    additional_tracks.append(
                        gen_track(
                            self,
                            track[0],
                            i,
                            enabled=True,
                            og=False,
                            conversion=track[1].conversion,
                            bitrate=track[1].bitrate,
                            downmix=track[1].downmix,
                        )
                    )

            self.tracks.extend(additional_tracks)

        super()._new_source(self.tracks)

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
                        dispositions=track.dispositions,
                    )
                )
        self.app.fastflix.current_video.video_settings.audio_tracks = tracks

    def reload(self, original_tracks: list[AudioTrack], audio_formats):
        disable_dups = (
            "nvencc" in self.main.convert_to.lower()
            or "vcenc" in self.main.convert_to.lower()
            or "qsvenc" in self.main.convert_to.lower()
        )

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
                dispositions=track.dispositions,
            )

            new_track.widgets.downmix.setCurrentText(track.downmix)
            new_track.widgets.convert_to.setCurrentText(track.conversion_codec)
            if track.conversion_codec in lossless:
                new_track.widgets.convert_bitrate.setDisabled(True)
                new_track.widgets.convert_bitrate.addItem("lossless")
                new_track.widgets.convert_bitrate.setCurrentText("lossless")
            else:
                if track.conversion_bitrate not in [
                    new_track.widgets.convert_bitrate.itemText(i)
                    for i in range(new_track.widgets.convert_bitrate.count())
                ]:
                    new_track.widgets.convert_bitrate.addItem(track.conversion_bitrate)
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
            track_info, tags = self._get_track_info(x)
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
            for idx, tk in enumerate(self.tracks):
                if tk.index > new_item.index:
                    print(f"Inserting at {idx}")
                    self.tracks.insert(idx, new_item)
                    break
            else:
                self.tracks.append(new_item)

        super()._new_source(self.tracks)
