#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Union

from box import Box
from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.encode import SubtitleTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import loading_movie, get_icon
from fastflix.shared import error_message, no_border
from fastflix.widgets.background_tasks import ExtractSubtitleSRT
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.widgets.windows.disposition import Disposition

disposition_options = [
    "none",
    "default",
    "dub",
    "original",
    "comment",
    "lyrics",
    "karaoke",
    "forced",
    "hearing_impaired",
]

subtitle_types = {
    "dvd_subtitle": "picture",
    "hdmv_pgs_subtitle": "picture",
    "dvdsub": "picture",
    "subrip": "text",
    "ssa": "text",
    "ass": "text",
    "mov_text": "text",
    "webvtt": "text",
    "xsub": "text",
}

language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

# TODO give warning about exact time needed for text based subtitles


class Subtitle(QtWidgets.QTabWidget):
    extract_completed_signal = QtCore.Signal()

    def __init__(self, parent, subtitle, index, enabled=True, first=False, dispositions=None):
        self.loading = True
        super(Subtitle, self).__init__(parent)
        self.parent = parent
        self.index = index
        self.outdex = None
        self.subtitle = Box(subtitle, default_box=True)
        self.first = first
        self.last = False
        self.subtitle_lang = subtitle.get("tags", {}).get("language")
        self.subtitle_type = subtitle_types.get(subtitle.get("codec_name", "text"), "text")
        self.setFixedHeight(60)

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{self.index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLabel(f"  {self.subtitle.codec_long_name}"),
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            enable_check=QtWidgets.QCheckBox(t("Preserve")),
            disposition=QtWidgets.QPushButton(),
            language=QtWidgets.QComboBox(),
            burn_in=QtWidgets.QCheckBox(t("Burn In")),
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)

        # self.widgets.disposition.addItems(dispositions)
        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)
        self.widgets.burn_in.toggled.connect(self.update_burn_in)
        # self.widgets.disposition.currentIndexChanged.connect(self.page_update)
        # self.widgets.disposition.setCurrentIndex(0)
        # for disposition, is_set in self.subtitle.disposition.items():
        #     if is_set:
        #         try:
        #             self.widgets.disposition.setCurrentIndex(dispositions.index(disposition))
        #         except ValueError:
        #             pass
        #         break
        # if self.subtitle.disposition.get("forced"):
        #     self.widgets.disposition.setCurrentIndex(dispositions.index("forced"))

        self.setFixedHeight(60)
        self.widgets.title.setToolTip(self.subtitle.to_yaml())
        self.widgets.burn_in.setToolTip(
            f"""{t("Overlay this subtitle track onto the video during conversion.")}\n
            {t("Please make sure seek method is set to exact")}.\n
            {t("Cannot remove afterwards!")}
            """
        )
        self.widgets.extract = QtWidgets.QPushButton(t("Extract"))
        self.widgets.extract.clicked.connect(self.extract)

        self.gif_label = QtWidgets.QLabel(self)
        self.movie = QtGui.QMovie(loading_movie)
        self.movie.setScaledSize(QtCore.QSize(25, 25))
        self.gif_label.setMovie(self.movie)
        # self.movie.start()

        self.dispositions = dispositions if dispositions else {k: False for k in disposition_options}
        if not dispositions:
            for disposition, is_set in self.subtitle.disposition.items():
                if is_set:
                    self.dispositions[disposition] = True

        self.disposition_widget = Disposition(self, f"Subtitle Track {index}", subs=True)
        self.set_dis_button()
        self.widgets.disposition.clicked.connect(self.disposition_widget.show)

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addWidget(QtWidgets.QLabel(t("Dispositions")))
        disposition_layout.addWidget(self.widgets.disposition)

        self.grid = QtWidgets.QGridLayout()
        self.grid.addLayout(self.init_move_buttons(), 0, 0)
        self.grid.addWidget(self.widgets.track_number, 0, 1)
        self.grid.addWidget(self.widgets.title, 0, 2)
        self.grid.setColumnStretch(2, True)
        if self.subtitle_type == "text":
            self.grid.addWidget(self.widgets.extract, 0, 3)
            self.grid.addWidget(self.gif_label, 0, 3)
            self.gif_label.hide()

        self.grid.addLayout(disposition_layout, 0, 4)
        self.grid.addWidget(self.widgets.burn_in, 0, 5)
        self.grid.addLayout(self.init_language(), 0, 6)

        self.grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(self.grid)
        self.loading = False
        self.updating_burn = False
        self.extract_completed_signal.connect(self.extraction_complete)

    def set_dis_button(self):
        output = ""
        for disposition, is_set in self.dispositions.items():
            if is_set:
                output += f"{t(disposition)},"
        if output:
            self.widgets.disposition.setText(output.rstrip(","))
        else:
            self.widgets.disposition.setText(t("none"))

    @property
    def dis_forced(self):
        return self.dispositions.get("forced", False)

    @property
    def dis_default(self):
        return self.dispositions.get("default", False)

    def extraction_complete(self):
        self.grid.addWidget(self.widgets.extract, 0, 3)
        self.movie.stop()
        self.gif_label.hide()
        self.widgets.extract.show()

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(20)
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def extract(self):
        worker = ExtractSubtitleSRT(self.parent.app, self.parent.main, self.index, self.extract_completed_signal)
        worker.start()
        self.gif_label.show()
        self.widgets.extract.hide()
        self.movie.start()

    def init_language(self):
        self.widgets.language.addItems(language_list)
        self.widgets.language.setMaximumWidth(110)
        try:
            self.widgets.language.setCurrentIndex(language_list.index(Lang(self.subtitle_lang).name))
        except Exception:
            self.widgets.language.setCurrentIndex(language_list.index("English"))
        self.widgets.language.currentIndexChanged.connect(self.page_update)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(t("Language")))
        layout.addWidget(self.widgets.language)
        return layout

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def set_outdex(self, outdex):
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{self.index}:{self.outdex}")

    # @property
    # def disposition(self):
    #     return None

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def language(self):
        return Lang(self.widgets.language.currentText()).pt2b

    @property
    def burn_in(self):
        return self.widgets.burn_in.isChecked()

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        self.widgets.track_number.setText(f"{self.index}:{self.outdex}" if enabled else "❌")
        self.parent.reorder(update=True)

    def update_burn_in(self):
        if self.updating_burn:
            return
        self.updating_burn = True
        enable = self.widgets.burn_in.isChecked()
        if enable and [1 for track in self.parent.tracks if track.enabled and track.burn_in and track is not self]:
            self.widgets.burn_in.setChecked(False)
            error_message(t("There is an existing burn-in track, only one can be enabled at a time"))
        if enable and self.parent.main.fast_time:
            self.parent.main.widgets.fast_time.setCurrentText("exact")
        self.updating_burn = False
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class SubtitleList(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(QtWidgets.QLabel(t("Subtitle Tracks")))
        top_layout.addStretch(1)

        self.remove_all_button = QtWidgets.QPushButton(t("Unselect All"))
        self.remove_all_button.setFixedWidth(150)
        self.remove_all_button.clicked.connect(lambda: self.select_all(False))
        self.save_all_button = QtWidgets.QPushButton(t("Preserve All"))
        self.save_all_button.setFixedWidth(150)
        self.save_all_button.clicked.connect(lambda: self.select_all(True))

        top_layout.addWidget(self.remove_all_button)
        top_layout.addWidget(self.save_all_button)

        super().__init__(app, parent, "Subtitle Tracks", "subtitle", top_row_layout=top_layout)
        self.main = parent.main
        self.app = app
        self._first_selected = False

    def select_all(self, select=True):
        for track in self.tracks:
            track.widgets.enable_check.setChecked(select)

    def lang_match(self, track: Union[Subtitle, dict], ignore_first=False):
        if not self.app.fastflix.config.opt("subtitle_select"):
            return False
        language = track.language if isinstance(track, Subtitle) else track.get("tags", {}).get("language", "")
        if not self.app.fastflix.config.opt("subtitle_select_preferred_language"):
            if (
                not ignore_first
                and self.app.fastflix.config.opt("subtitle_select_first_matching")
                and self._first_selected
            ):
                return False
            self._first_selected = True
            return True
        try:
            track_lang = Lang(language)
        except InvalidLanguageValue:
            return True
        else:
            if Lang(self.app.fastflix.config.opt("subtitle_language")) == track_lang:
                if (
                    not ignore_first
                    and self.app.fastflix.config.opt("subtitle_select_first_matching")
                    and self._first_selected
                ):
                    return False
                self._first_selected = True
                return True
        return False

    def new_source(self):
        self.tracks = []
        self._first_selected = False
        for index, track in enumerate(self.app.fastflix.current_video.streams.subtitle):
            enabled = self.lang_match(track)
            new_item = Subtitle(self, track, index=track.index, first=True if index == 0 else False, enabled=enabled)
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        if self.app.fastflix.config.opt("subtitle_automatic_burn_in"):
            first_default, first_forced = None, None
            for track in self.tracks:
                if not first_default and track.dis_default and self.lang_match(track, ignore_first=True):
                    first_default = track
                    break
                if not first_forced and track.dis_forced and self.lang_match(track, ignore_first=True):
                    first_forced = track
                    break
            if not self.app.fastflix.config.disable_automatic_subtitle_burn_in:
                if first_forced is not None:
                    first_forced.widgets.burn_in.setChecked(True)
                elif first_default is not None:
                    first_default.widgets.burn_in.setChecked(True)

        super()._new_source(self.tracks)
        self.get_settings()

    def get_settings(self):
        tracks = []
        burn_in_count = 0
        for track in self.tracks:
            if track.enabled:
                tracks.append(
                    SubtitleTrack(
                        index=track.index,
                        outdex=track.outdex,
                        dispositions=track.dispositions,
                        language=track.language,
                        burn_in=track.burn_in,
                        subtitle_type=track.subtitle_type,
                    )
                )
                if track.burn_in:
                    burn_in_count += 1
        if burn_in_count > 1:
            raise FastFlixInternalException(t("More than one track selected to burn in"))
        self.app.fastflix.current_video.video_settings.subtitle_tracks = tracks

    def reload(self, original_tracks):
        enabled_tracks = [x.index for x in original_tracks]
        self.new_source()
        for track in self.tracks:
            enabled = track.index in enabled_tracks
            track.widgets.enable_check.setChecked(enabled)
            if enabled:
                existing_track = [x for x in original_tracks if x.index == track.index][0]
                track.dispositions = existing_track.dispositions.copy()
                track.set_dis_button()
                track.widgets.burn_in.setChecked(existing_track.burn_in)
                track.widgets.language.setCurrentText(Lang(existing_track.language).name)
        super()._new_source(self.tracks)
