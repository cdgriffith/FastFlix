#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box
from iso639 import Lang
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import SubtitleTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import down_arrow_icon, up_arrow_icon
from fastflix.shared import FastFlixInternalException, error_message, main_width
from fastflix.widgets.panels.abstract_list import FlixList

dispositions = [
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


language_list = sorted((k for k, v in Lang._data["name"].items() if v["pt2B"] and v["pt1"]), key=lambda x: x.lower())

# TODO add fake empty subtitle track?


class Subtitle(QtWidgets.QTabWidget):
    def __init__(self, parent, subtitle, index, enabled=True, first=False):
        self.loading = True
        super(Subtitle, self).__init__(parent)
        self.parent = parent
        self.index = index
        self.outdex = None
        self.subtitle = Box(subtitle, default_box=True)
        self.first = first
        self.last = False
        self.subtitle_lang = subtitle.get("tags", {}).get("language")

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{self.index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLabel(f"  {self.subtitle.codec_long_name}"),
            up_button=QtWidgets.QPushButton(QtGui.QIcon(up_arrow_icon), ""),
            down_button=QtWidgets.QPushButton(QtGui.QIcon(down_arrow_icon), ""),
            enable_check=QtWidgets.QCheckBox(t("Preserve")),
            disposition=QtWidgets.QComboBox(),
            language=QtWidgets.QComboBox(),
            burn_in=QtWidgets.QCheckBox(t("Burn In")),
        )

        self.widgets.up_button.setStyleSheet("""QPushButton, QPushButton:hover{border-width: 0;}""")
        self.widgets.down_button.setStyleSheet("""QPushButton, QPushButton:hover{border-width: 0;}""")

        self.widgets.disposition.addItems(dispositions)
        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)
        self.widgets.burn_in.toggled.connect(self.update_burn_in)
        self.widgets.disposition.currentIndexChanged.connect(self.page_update)
        self.widgets.disposition.setCurrentIndex(0)
        for disposition, is_set in self.subtitle.disposition.items():
            if is_set:
                try:
                    self.widgets.disposition.setCurrentIndex(dispositions.index(disposition))
                except ValueError:
                    pass  # TODO figure out all possible dispositions for subtitles / log if issue
                break

        self.setFixedHeight(60)
        self.widgets.title.setToolTip(self.subtitle.to_yaml())
        self.widgets.burn_in.setToolTip(
            t("Overlay this subtitle track onto the video during conversion. Cannot remove afterwards.")
        )

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addStretch()
        disposition_layout.addWidget(QtWidgets.QLabel("Disposition"))
        disposition_layout.addWidget(self.widgets.disposition)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.title, 0, 2)
        grid.addLayout(disposition_layout, 0, 4)
        grid.addWidget(self.widgets.burn_in, 0, 5)
        grid.addLayout(self.init_language(), 0, 6)
        # grid.addWidget(self.init_extract_button(), 0, 6)
        grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(grid)
        self.loading = False
        self.updating_burn = False

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

    #
    # def init_extract_button(self):
    #     self.widgets.extract = QtWidgets.QPushButton("Extract")
    #     self.widgets.extract.clicked.connect(self.extract)
    #     return self.widgets.extract
    #
    # def extract(self):
    #     from fastflix.widgets.command_runner import BackgroundRunner
    #     self.parent.main.flix.execute(
    #         f'"{self.parent.main.flix.ffmpeg}" -i "{self.parent.main.input_video}" -map 0:{self.index} -c srt -f srt "{self.parent.main.input_video}.{self.index}.srt"',
    #         work_dir=self.parent.main.path.work
    #     )

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

    @property
    def disposition(self):
        return None if self.widgets.disposition.currentIndex() == 0 else self.widgets.disposition.currentText()

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
        self.updating_burn = False
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class SubtitleList(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(app, parent, "Subtitle Tracks", "subtitle")
        self.main = parent.main
        self.app = app

    def new_source(self):
        self.tracks = []
        for index, track in enumerate(self.app.fastflix.current_video.streams.subtitle):
            enabled = True
            if self.app.fastflix.config.opt("subtitle_only_preferred_language"):
                enabled = False
                if Lang(self.app.fastflix.config.opt("subtitle_language")) == Lang(
                    track.get("tags", {}).get("language")
                ):
                    enabled = True
            new_item = Subtitle(self, track, index=track.index, first=True if index == 0 else False, enabled=enabled)
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        if self.app.fastflix.config.opt("subtitle_automatic_burn_in"):
            first_default, first_forced = None, None
            for track in self.tracks:
                if not first_default and track.disposition == "default":
                    first_default = track
                if not first_forced and track.disposition == "forced":
                    first_forced = track
            if not self.app.fastflix.config.disable_automatic_subtitle_burn_in:
                if first_forced is not None:
                    first_forced.widgets.burn_in.setChecked(True)
                elif first_default is not None:
                    first_default.widgets.burn_in.setChecked(True)

        super()._new_source(self.tracks)

    def get_settings(self):
        tracks = []
        burn_in_count = 0
        for track in self.tracks:
            if track.enabled:
                tracks.append(
                    SubtitleTrack(
                        index=track.index,
                        outdex=track.outdex,
                        disposition=track.disposition,
                        language=track.language,
                        burn_in=track.burn_in,
                    )
                )
                if track.burn_in:
                    burn_in_count += 1
        if burn_in_count > 1:
            raise FastFlixInternalException(t("More than one track selected to burn in"))
        self.app.fastflix.current_video.video_settings.subtitle_tracks = tracks
