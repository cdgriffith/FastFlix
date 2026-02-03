#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from iso639 import iter_langs
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtGui, QtWidgets

from fastflix.language import t, Language
from fastflix.models.encode import AudioTrack
from fastflix.models.profiles import Profile, TitleMode
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon
from fastflix.ui_scale import scaler
from fastflix.ui_constants import HEIGHTS, WIDTHS
from fastflix.ui_styles import get_onyx_disposition_style
from fastflix.shared import no_border, error_message, yes_no_message, clear_list
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.audio_processing import apply_audio_filters
from fastflix.widgets.windows.audio_conversion import AudioConversion
from fastflix.widgets.windows.disposition import Disposition

language_list = [v.name for v in iter_langs() if v.pt2b and v.pt1] + ["Undefined"]
logger = logging.getLogger("fastflix")

# Mapping of channel counts to friendly names
channels_to_layout = {
    1: "Mono",
    2: "Stereo",
    3: "2.1",
    4: "4.0",
    5: "5.0",
    6: "5.1",
    7: "6.1",
    8: "7.1",
}

# Mapping of codec names to friendly display names
codec_display_names = {
    "aac": "AAC",
    "ac3": "AC3",
    "eac3": "E-AC3",
    "truehd": "TrueHD",
    "dts": "DTS",
    "dca": "DTS",
    "flac": "FLAC",
    "alac": "ALAC",
    "opus": "Opus",
    "libopus": "Opus",
    "vorbis": "Vorbis",
    "libvorbis": "Vorbis",
    "mp3": "MP3",
    "libmp3lame": "MP3",
    "pcm_s16le": "PCM",
    "pcm_s24le": "PCM",
    "pcm_s32le": "PCM",
}


def generate_audio_title(codec: str, channels: int, downmix: str | None = None) -> str:
    """Generate a friendly audio title like 'TrueHD 5.1' from codec and channel info."""
    # Get friendly codec name
    codec_lower = codec.lower() if codec else ""
    friendly_codec = codec_display_names.get(codec_lower, codec.upper() if codec else "Audio")

    # Determine channel layout
    if downmix and downmix != "No Downmix":
        # Use downmix layout directly (e.g., "stereo", "5.1")
        channel_layout = downmix
    else:
        # Use channel count to determine layout
        channel_layout = channels_to_layout.get(channels, f"{channels}ch")

    return f"{friendly_codec} {channel_layout}"


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
        app,
        parent,
        index,
        disabled_dup=False,
    ):
        self.loading = True
        super(Audio, self).__init__(parent)
        self.app = app
        self.setObjectName("Audio")
        self.parent: "AudioList" = parent
        self.index = index
        self.first = False
        self.last = False
        self.setFixedHeight(scaler.scale(HEIGHTS.PANEL_ITEM))
        audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[index]

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{audio_track.index}:{audio_track.outdex}" if audio_track.enabled else "❌"),
            title=QtWidgets.QLineEdit(audio_track.title),
            audio_info=QtWidgets.QLabel(audio_track.friendly_info),
            up_button=QtWidgets.QPushButton(QtGui.QIcon(get_icon("up-arrow", self.app.fastflix.config.theme)), ""),
            down_button=QtWidgets.QPushButton(QtGui.QIcon(get_icon("down-arrow", self.app.fastflix.config.theme)), ""),
            enable_check=QtWidgets.QCheckBox(t("Enabled")),
            dup_button=QtWidgets.QPushButton(QtGui.QIcon(get_icon("onyx-copy", self.app.fastflix.config.theme)), ""),
            delete_button=QtWidgets.QPushButton(QtGui.QIcon(get_icon("black-x", self.app.fastflix.config.theme)), ""),
            language=QtWidgets.QComboBox(),
            convert_to=None,
            convert_bitrate=None,
            disposition=QtWidgets.QPushButton(),
            conversion=QtWidgets.QPushButton(t("Conversion")),
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)
        self.widgets.dup_button.setStyleSheet(no_border)
        self.widgets.delete_button.setStyleSheet(no_border)

        self.widgets.audio_info.setToolTip(Box(audio_track.raw_info).to_yaml())

        self.widgets.language.addItems(["No Language Set", "Undefined"] + language_list)
        self.widgets.language.setMaximumWidth(150)
        if audio_track.language:
            try:
                lang = Language(audio_track.language).name
            except InvalidLanguageValue:
                pass
            else:
                if lang in language_list:
                    self.widgets.language.setCurrentText(lang)

        self.widgets.language.currentIndexChanged.connect(self.page_update)
        self.widgets.title.setFixedWidth(scaler.scale(WIDTHS.AUDIO_TITLE))
        self.widgets.title.textChanged.connect(self.page_update)
        # self.widgets.audio_info.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.widgets.audio_info.setFixedWidth(scaler.scale(WIDTHS.AUDIO_INFO))

        self.widgets.enable_check.setChecked(audio_track.enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)

        self.widgets.dup_button.clicked.connect(lambda: self.dup_me())
        self.widgets.dup_button.setFixedWidth(scaler.scale(17))
        if disabled_dup:
            self.widgets.dup_button.hide()
            self.widgets.dup_button.setDisabled(True)

        self.widgets.delete_button.clicked.connect(lambda: self.del_me())
        self.widgets.delete_button.setFixedWidth(scaler.scale(17))

        self.widgets.track_number.setFixedWidth(scaler.scale(17))

        self.disposition_widget = Disposition(
            app=app, parent=self, track_name=f"Audio Track {index}", track_index=index, audio=True
        )
        self.widgets.disposition.clicked.connect(self.disposition_widget.show)

        self.widgets.conversion.clicked.connect(self.show_conversions)

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addWidget(self.widgets.disposition)
        self.widgets.disposition.setText(t("Dispositions"))

        label = QtWidgets.QLabel(f"{t('Title')}: ")
        self.widgets.title.setFixedWidth(scaler.scale(WIDTHS.AUDIO_TITLE))
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
        grid.addWidget(self.widgets.conversion, 0, 5)
        grid.addWidget(self.widgets.language, 0, 6)

        right_button_start_index = 7

        if not audio_track.original:
            spacer = QtWidgets.QLabel()
            spacer.setFixedWidth(scaler.scale(53))
            grid.addWidget(spacer, 0, right_button_start_index)
            grid.addWidget(self.widgets.delete_button, 0, right_button_start_index + 1)
        else:
            grid.addWidget(self.widgets.enable_check, 0, right_button_start_index)
            grid.addWidget(self.widgets.dup_button, 0, right_button_start_index + 1)
        self.setLayout(grid)
        self.check_dis_button()
        self.conversion_box = None
        self.loading = False

    def show_conversions(self):
        try:
            self.conversion_box.close()
        except Exception:
            pass
        try:
            del self.conversion_box
        except Exception:
            pass

        self.conversion_box = AudioConversion(
            self.app,
            track_index=self.index,
            encoders=self.app.fastflix.audio_encoders,
            audio_track_update=self.page_update,
        )
        self.conversion_box.show()

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        # layout.setMargin(0)
        # self.widgets.up_button = QtWidgets.QPushButton("^")
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(scaler.scale(17))
        self.widgets.up_button.setFixedHeight(scaler.scale(20))
        self.widgets.up_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        # self.widgets.down_button = QtWidgets.QPushButton("v")
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(scaler.scale(17))
        self.widgets.down_button.setFixedHeight(scaler.scale(20))
        self.widgets.down_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        audio_track = self.app.fastflix.current_video.audio_tracks[self.index]
        audio_track.enabled = enabled
        self.widgets.track_number.setText(f"{audio_track.index}:{audio_track.outdex}" if enabled else "❌")
        self.parent.reorder(update=True)
        # self.parent.parent.subtitles.reorder()

    def page_update(self):
        self.app.fastflix.current_video.audio_tracks[self.index].title = self.title
        self.app.fastflix.current_video.audio_tracks[self.index].language = self.language
        if not self.loading:
            self.check_conversion_button()
            self.check_dis_button()
            return self.parent.main.page_update(build_thumbnail=False)

    @property
    def enabled(self):
        try:
            return self.app.fastflix.current_video.audio_tracks[self.index].enabled
        except IndexError:
            return False

    @property
    def language(self) -> str:
        if self.widgets.language.currentIndex() == 0:
            return ""
        return Language(self.widgets.language.currentText()).pt2b

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
        # Add new track to the conversion list
        new_track = self.app.fastflix.current_video.audio_tracks[self.index].copy()
        new_track.outdex = len(self.app.fastflix.current_video.audio_tracks) + 1
        new_track.original = False
        self.app.fastflix.current_video.audio_tracks.append(new_track)

        # Add new track to GUI
        new_item = Audio(
            parent=self.parent,
            app=self.app,
            index=len(self.app.fastflix.current_video.audio_tracks) - 1,
            disabled_dup=(
                "nvencc" in self.parent.main.convert_to.lower()
                or "vcenc" in self.parent.main.convert_to.lower()
                or "qsvenc" in self.parent.main.convert_to.lower()
            ),
        )
        self.parent.tracks.append(new_item)
        self.parent.reorder()

    def del_me(self):
        self.parent.remove_track(self)
        del self.app.fastflix.current_video.audio_tracks[self.index]
        self.parent.reorder(update=True)

    def set_outdex(self, outdex):
        self.app.fastflix.current_video.audio_tracks[self.index].outdex = outdex
        audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[self.index]
        self.outdex = outdex
        if not audio_track.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{audio_track.index}:{audio_track.outdex}")

    def close(self) -> bool:
        del self.widgets
        return super().close()

    def update_track(self, conversion=None, bitrate=None, downmix=None, title=None):
        audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[self.index]
        if conversion:
            audio_track.conversion_codec = conversion
        if bitrate:
            audio_track.conversion_bitrate = bitrate
        if downmix:
            audio_track.downmix = downmix
        if title is not None:
            audio_track.title = title
            self.widgets.title.setText(title)
        self.page_update()

    def check_conversion_button(self):
        audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[self.index]
        if audio_track.conversion_codec:
            self.widgets.conversion.setStyleSheet(get_onyx_disposition_style(enabled=True))
            self.widgets.conversion.setText(t("Conversion") + f": {audio_track.conversion_codec}")
        else:
            self.widgets.conversion.setStyleSheet(get_onyx_disposition_style(enabled=False))
            self.widgets.conversion.setText(t("Conversion"))

    def check_dis_button(self):
        audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[self.index]
        if any(audio_track.dispositions.values()):
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=True))
        else:
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=False))


class AudioList(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        super(AudioList, self).__init__(app, parent, "Audio Tracks", "audio")
        self.available_audio_encoders = app.fastflix.audio_encoders
        self.app = app
        self.parent = parent
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
        if not self.app.fastflix.current_video:
            return
        clear_list(self.tracks, close=True)
        self.app.fastflix.current_video.audio_tracks = []
        self.tracks: list[Audio] = []
        self._first_selected = False
        for i, x in enumerate(self.app.fastflix.current_video.streams.audio):
            track_info, tags = self._get_track_info(x)
            self.app.fastflix.current_video.audio_tracks.append(
                AudioTrack(
                    index=x.index,
                    outdex=i + 1,
                    title=tags.get("title", ""),
                    language=tags.get("language", ""),
                    profile=x.get("profile"),
                    channels=x.channels,
                    enabled=True,
                    original=True,
                    raw_info=x,
                    friendly_info=track_info,
                    dispositions={k: bool(v) for k, v in x.disposition.items()},
                )
            )
            new_item = Audio(
                parent=self,
                app=self.app,
                index=i,
                disabled_dup=(
                    "nvencc" in self.main.convert_to.lower()
                    or "vcenc" in self.main.convert_to.lower()
                    or "qsvenc" in self.main.convert_to.lower()
                ),
            )
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()
        super()._new_source(self.tracks)
        # self.update_audio_settings()

    def allowed_formats(self, allowed_formats=None):
        disable_dups = (
            "nvencc" in self.main.convert_to.lower()
            or "vcenc" in self.main.convert_to.lower()
            or "qsvenc" in self.main.convert_to.lower()
        )
        tracks_need_removed = False
        for track in self.tracks:
            audio_track: AudioTrack = self.app.fastflix.current_video.audio_tracks[track.index]
            track.widgets.dup_button.setDisabled(disable_dups)
            if not audio_track.original:
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
        # for track in self.tracks:
        #     track.update_codecs(allowed_formats or set())

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

        clear_list(self.tracks)

        def gen_track(
            parent,
            audio_track,
            outdex,
            og=False,
            enabled=True,
            downmix=None,
            conversion=None,
            bitrate=None,
            title_mode=None,
            custom_title=None,
        ) -> Audio:
            track_info, tags = self._get_track_info(audio_track)

            # Determine title based on title_mode
            if title_mode == TitleMode.NO_TITLE:
                title = ""
            elif title_mode == TitleMode.GENERATE:
                # Generate title from codec and channel info
                codec = conversion if conversion else audio_track.codec_name
                title = generate_audio_title(codec, audio_track.channels, downmix)
            elif title_mode == TitleMode.CUSTOM:
                # Use custom title from the audio match
                title = custom_title if custom_title else ""
            else:
                # Original title (default)
                title = tags.get("title", "")

            self.app.fastflix.current_video.audio_tracks.append(
                AudioTrack(
                    index=audio_track.index,
                    outdex=outdex,
                    title=title,
                    language=tags.get("language", ""),
                    profile=audio_track.get("profile"),
                    channels=audio_track.channels,
                    enabled=enabled,
                    original=og,
                    raw_info=audio_track,
                    friendly_info=track_info,
                    downmix=downmix,
                    conversion_codec=conversion,
                    conversion_bitrate=bitrate,
                    dispositions={k: bool(v) for k, v in audio_track.disposition.items()},
                )
            )
            new_item = Audio(
                parent=parent,
                app=self.app,
                index=len(self.app.fastflix.current_video.audio_tracks) - 1,
                disabled_dup=(
                    "nvencc" in self.main.convert_to.lower()
                    or "vcenc" in self.main.convert_to.lower()
                    or "qsvenc" in self.main.convert_to.lower()
                ),
            )
            self.tracks.append(new_item)

            return new_item

        self.new_source(audio_formats)

        # # First populate all original tracks and disable them
        # for i, track in enumerate(original_tracks, start=1):
        #     self.tracks.append(gen_track(self, track, outdex=i, og=True, enabled=False))

        tracks = apply_audio_filters(profile.audio_filters, original_tracks=original_tracks)

        for track in self.tracks:
            track.widgets.enable_check.setChecked(False)

        if profile.audio_filters is not False and self.tracks and not tracks:
            enable = yes_no_message(
                t("No audio tracks matched for this profile, enable first track?"), title="No Audio Match"
            )
            if enable:
                self.tracks[0].widgets.enable_check.setChecked(True)
            return

        # Apply first set of conversions to the original audio tracks
        # Build a mapping from stream index to self.tracks position
        stream_index_to_track = {
            self.app.fastflix.current_video.audio_tracks[i].index: i for i in range(len(self.tracks))
        }
        current_id = -1
        skip_tracks = []
        for idx, track in enumerate(tracks):
            # track[0] is the Box() track object, track[1] is the AudioMatch it matched against
            if track[0].index > current_id:
                current_id = track[0].index
                track_pos = stream_index_to_track.get(track[0].index)
                if track_pos is not None:
                    self.tracks[track_pos].widgets.enable_check.setChecked(True)

                    # Determine title based on title_mode
                    title_mode = track[1].title_mode
                    if title_mode == TitleMode.NO_TITLE:
                        title = ""
                    elif title_mode == TitleMode.GENERATE:
                        codec = track[1].conversion if track[1].conversion else track[0].codec_name
                        title = generate_audio_title(codec, track[0].channels, track[1].downmix)
                    elif title_mode == TitleMode.CUSTOM:
                        title = track[1].custom_title if track[1].custom_title else ""
                    else:
                        title = None  # Keep original

                    self.tracks[track_pos].update_track(
                        downmix=track[1].downmix,
                        conversion=track[1].conversion,
                        bitrate=track[1].bitrate,
                        title=title,
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
                            title_mode=track[1].title_mode,
                            custom_title=track[1].custom_title,
                        )
                    )

            self.tracks.extend(additional_tracks)

        super()._new_source(self.tracks)

    def update_audio_settings(self):
        return  # TODO remove

    def reload(self, original_tracks: list[AudioTrack], audio_formats):
        clear_list(self.tracks)
        disable_dups = (
            "nvencc" in self.main.convert_to.lower()
            or "vcenc" in self.main.convert_to.lower()
            or "qsvenc" in self.main.convert_to.lower()
        )

        for i, track in enumerate(self.app.fastflix.current_video.audio_tracks):
            self.tracks.append(
                Audio(
                    app=self.app,
                    parent=self,
                    index=i,
                    disabled_dup=disable_dups,
                )
            )

        super()._new_source(self.tracks)

    def move_up(self, widget):
        self.app.fastflix.current_video.audio_tracks.insert(
            widget.index - 1, self.app.fastflix.current_video.audio_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index - 1, self.tracks.pop(index))
        self.reorder()

    def move_down(self, widget):
        self.app.fastflix.current_video.audio_tracks.insert(
            widget.index + 1, self.app.fastflix.current_video.audio_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index + 1, self.tracks.pop(index))
        self.reorder()
