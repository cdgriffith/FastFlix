#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Union

from box import Box
from iso639 import iter_langs
from iso639.exceptions import InvalidLanguageValue
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t, Language
from fastflix.models.encode import SubtitleTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import loading_movie, get_icon
from fastflix.shared import error_message, no_border, clear_list
from fastflix.ui_scale import scaler
from fastflix.ui_styles import get_onyx_disposition_style
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
    "hdmv_pgs_subtitle": "pgs",
    "dvdsub": "picture",
    "subrip": "text",
    "ssa": "text",
    "ass": "text",
    "mov_text": "text",
    "webvtt": "text",
    "xsub": "text",
}

language_list = [v.name for v in iter_langs() if v.pt2b and v.pt1] + ["Undefined"]

# TODO give warning about exact time needed for text based subtitles


class Subtitle(QtWidgets.QTabWidget):
    extract_completed_signal = QtCore.Signal(str)

    def __init__(self, app, parent, index, enabled=True, first=False):
        self.loading = True
        super(Subtitle, self).__init__(parent)
        self.app = app
        self.parent: "SubtitleList" = parent
        self.setObjectName("Subtitle")
        self.index = index
        self.outdex = None
        self.first = first
        self.last = False
        # self.setFixedHeight(180)
        sub_track: SubtitleTrack = self.app.fastflix.current_video.subtitle_tracks[index]
        long_name = (
            f"  {sub_track.long_name}" if sub_track.long_name else f"  {t('Subtitle Type')}:{sub_track.subtitle_type}"
        )

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{sub_track.index}:{sub_track.outdex}" if enabled else "❌"),
            title=QtWidgets.QLabel(long_name),
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            enable_check=QtWidgets.QCheckBox(t("Preserve")),
            disposition=QtWidgets.QPushButton(t("Dispositions")),
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
        self.widgets.title.setToolTip(Box(sub_track.raw_info).to_yaml())
        self.widgets.burn_in.setToolTip(
            f"""{t("Overlay this subtitle track onto the video during conversion.")}\n
            {t("Please make sure seek method is set to exact")}.\n
            {t("Cannot remove afterwards!")}
            """
        )

        # Setup extract button with OCR option for PGS subtitles
        if sub_track.subtitle_type == "pgs":
            self.widgets.extract = QtWidgets.QPushButton(t("Extract"))
            extract_menu = QtWidgets.QMenu(self)

            # Always offer .sup extraction (fast, no dependencies)
            extract_menu.addAction(t("Extract as .sup (image - fast)"), lambda: self.extract(use_ocr=False))

            # Check if OCR dependencies are available
            ocr_action = extract_menu.addAction(
                t("Convert to .srt (OCR - 3-5 min)"), lambda: self.extract(use_ocr=True)
            )

            # Enable OCR option only if dependencies are available
            if not self.app.fastflix.config.pgs_ocr_available:
                ocr_action.setEnabled(False)
                ocr_action.setToolTip(t("Missing dependencies: tesseract or pgsrip"))

            self.widgets.extract.setMenu(extract_menu)
            # Scale the dropdown arrow to match the up/down button icon sizes
            arrow_size = scaler.scale(12)
            arrow_right = scaler.scale(6)
            arrow_pad = arrow_size + arrow_right + scaler.scale(4)
            self.widgets.extract.setStyleSheet(
                f"QPushButton {{ padding-right: {arrow_pad}px; }}"
                f" QPushButton::menu-indicator {{ width: {arrow_size}px; height: {arrow_size}px;"
                f" subcontrol-position: right center; subcontrol-origin: padding;"
                f" right: {arrow_right}px; }}"
            )
        else:
            self.widgets.extract = QtWidgets.QPushButton(t("Extract"))
            self.widgets.extract.clicked.connect(self.extract)

        self.gif_label = QtWidgets.QLabel(self)
        self.movie = QtGui.QMovie(loading_movie)
        self.movie.setScaledSize(QtCore.QSize(25, 25))
        self.gif_label.setMovie(self.movie)

        self.cancel_button = QtWidgets.QPushButton(t("Cancel"))
        self.cancel_button.clicked.connect(self.cancel_extraction)
        self.cancel_button.hide()

        self.view_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-file-search", self.parent.app.fastflix.config.theme)), ""
        )
        self.view_button.setToolTip(t("Open containing folder"))
        self.view_button.setFixedWidth(scaler.scale(30))
        self.view_button.clicked.connect(self.view_extracted_file)
        self.view_button.hide()

        self._worker = None
        self._last_extracted_path = ""

        self.disposition_widget = Disposition(
            app=self.app, parent=self, track_name=f"Subtitle Track {index}", track_index=index, audio=False
        )
        # self.set_dis_button()
        self.widgets.disposition.clicked.connect(self.disposition_widget.show)

        disposition_layout = QtWidgets.QHBoxLayout()
        # disposition_layout.addWidget(QtWidgets.QLabel(t("Dispositions")))
        disposition_layout.addWidget(self.widgets.disposition)

        self.grid = QtWidgets.QGridLayout()
        self.grid.addLayout(self.init_move_buttons(), 0, 0)
        self.grid.addWidget(self.widgets.track_number, 0, 1)
        self.grid.addWidget(self.widgets.title, 0, 2)
        self.grid.setColumnStretch(2, True)
        if sub_track.subtitle_type in ["text", "pgs"]:
            self.extract_container = QtWidgets.QWidget()
            extract_layout = QtWidgets.QHBoxLayout()
            extract_layout.setContentsMargins(0, 0, 0, 0)
            extract_layout.setSpacing(2)
            extract_layout.addWidget(self.widgets.extract)
            extract_layout.addWidget(self.gif_label)
            extract_layout.addWidget(self.cancel_button)
            extract_layout.addWidget(self.view_button)
            self.extract_container.setLayout(extract_layout)
            self.grid.addWidget(self.extract_container, 0, 3)
            self.gif_label.hide()

        self.grid.addLayout(disposition_layout, 0, 4)
        self.grid.addWidget(self.widgets.burn_in, 0, 5)
        self.grid.addLayout(self.init_language(sub_track), 0, 6)

        self.grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(self.grid)
        self.check_dis_button()
        self.loading = False
        self.updating_burn = False
        self.extract_completed_signal.connect(self.extraction_complete)

    def extraction_complete(self, path: str = ""):
        self.movie.stop()
        self.gif_label.hide()
        self.cancel_button.hide()
        self.widgets.extract.show()
        self._worker = None
        if path:
            self._last_extracted_path = path
            self.view_button.show()
        else:
            self.view_button.hide()

    def cancel_extraction(self):
        if self._worker is not None:
            self._worker.cancel()
        self.movie.stop()
        self.gif_label.hide()
        self.cancel_button.hide()
        self.widgets.extract.show()

    def view_extracted_file(self):
        if self._last_extracted_path:
            parent_dir = str(Path(self._last_extracted_path).parent)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(parent_dir))

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(scaler.scale(17))
        self.widgets.up_button.setFixedHeight(scaler.scale(20))
        self.widgets.up_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(scaler.scale(17))
        self.widgets.down_button.setFixedHeight(scaler.scale(20))
        self.widgets.down_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def _get_extract_extension(self, use_ocr=False):
        """Determine the file extension for subtitle extraction."""
        sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
        if sub_track.subtitle_type == "pgs":
            return "srt" if use_ocr else "sup"
        codec_name = sub_track.raw_info.get("codec_name", "").lower() if sub_track.raw_info else ""
        if codec_name == "ass":
            return "ass"
        elif codec_name == "ssa":
            return "ssa"
        return "srt"

    def extract(self, use_ocr=False):
        extension = self._get_extract_extension(use_ocr=use_ocr)
        output_dir = Path(self.parent.main.output_video).parent
        input_name = Path(self.parent.main.input_video).stem
        default_name = f"{input_name}.{self.index}.{self.language}.{extension}"
        default_path = str(output_dir / default_name)

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption=t("Save Subtitle As"),
            dir=default_path,
            filter=f"{t('Subtitle Files')} (*.{extension})",
        )
        if not filename:
            return

        self._worker = ExtractSubtitleSRT(
            self.parent.app,
            self.parent.main,
            self.index,
            self.extract_completed_signal,
            language=self.language,
            use_ocr=use_ocr,
            output_path=filename,
        )
        self._worker.start()
        self.widgets.extract.hide()
        self.view_button.hide()
        self.gif_label.show()
        self.cancel_button.show()
        self.movie.start()

    def init_language(self, sub_track: SubtitleTrack):
        self.widgets.language.addItems(language_list)
        self.widgets.language.setMaximumWidth(110)
        try:
            self.widgets.language.setCurrentIndex(language_list.index(Language(sub_track.language).name))
        except Exception:
            self.widgets.language.setCurrentIndex(language_list.index("English"))
        self.widgets.language.currentIndexChanged.connect(self.update_language)
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
        self.app.fastflix.current_video.subtitle_tracks[self.index].outdex = outdex
        sub_track: SubtitleTrack = self.app.fastflix.current_video.subtitle_tracks[self.index]
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{sub_track.index}:{sub_track.outdex}")

    @property
    def enabled(self):
        try:
            return self.app.fastflix.current_video.subtitle_tracks[self.index].enabled
        except IndexError:
            return False

    @property
    def language(self):
        return Language(self.widgets.language.currentText()).pt2b

    @property
    def burn_in(self):
        return self.widgets.burn_in.isChecked()

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
        sub_track.enabled = enabled
        self.widgets.track_number.setText(f"{sub_track.index}:{sub_track.outdex}" if enabled else "❌")
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
            self.parent.main.widgets.fast_time.setCurrentIndex(1)  # Set to "Exact"
        sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
        sub_track.burn_in = enable
        self.updating_burn = False
        self.page_update()

    def update_language(self):
        if not self.loading:
            sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
            sub_track.language = self.language
            self.page_update()

    def page_update(self):
        if not self.loading:
            self.check_dis_button()
            return self.parent.main.page_update(build_thumbnail=False)

    def check_dis_button(self):
        track: SubtitleTrack = self.app.fastflix.current_video.subtitle_tracks[self.index]
        if any(track.dispositions.values()):
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=True))
        else:
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=False))


ext_subtitle_types = {
    ".srt": "text",
    ".ass": "text",
    ".ssa": "text",
    ".vtt": "text",
    ".sup": "picture",
}


class ExternalSubtitle(QtWidgets.QTabWidget):
    def __init__(self, app, parent, index, enabled=True, first=False):
        self.loading = True
        super(ExternalSubtitle, self).__init__(parent)
        self.app = app
        self.parent: "SubtitleList" = parent
        self.setObjectName("Subtitle")
        self.index = index
        self.outdex = None
        self.first = first
        self.last = False

        sub_track: SubtitleTrack = self.app.fastflix.current_video.subtitle_tracks[index]
        filename = Path(sub_track.file_path).name if sub_track.file_path else "unknown"

        self.widgets = Box(
            track_number=QtWidgets.QLabel("[EXT]" if enabled else "❌"),
            title=QtWidgets.QLabel(f"  [EXT] {filename}"),
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            enable_check=QtWidgets.QCheckBox(t("Preserve")),
            disposition=QtWidgets.QPushButton(t("Dispositions")),
            language=QtWidgets.QComboBox(),
            burn_in=QtWidgets.QCheckBox(t("Burn In")),
            remove_button=QtWidgets.QPushButton(t("Remove")),
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)

        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)
        self.widgets.burn_in.toggled.connect(self.update_burn_in)
        self.widgets.remove_button.clicked.connect(self.remove)

        self.setFixedHeight(60)
        self.widgets.title.setToolTip(str(sub_track.file_path))
        self.widgets.burn_in.setToolTip(
            f"""{t("Overlay this subtitle track onto the video during conversion.")}\n
            {t("Please make sure seek method is set to exact")}.\n
            {t("Cannot remove afterwards!")}
            """
        )

        self.disposition_widget = Disposition(
            app=self.app, parent=self, track_name=f"Subtitle Track {index}", track_index=index, audio=False
        )
        self.widgets.disposition.clicked.connect(self.disposition_widget.show)

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addWidget(self.widgets.disposition)

        self.grid = QtWidgets.QGridLayout()
        self.grid.addLayout(self.init_move_buttons(), 0, 0)
        self.grid.addWidget(self.widgets.track_number, 0, 1)
        self.grid.addWidget(self.widgets.title, 0, 2)
        self.grid.setColumnStretch(2, True)
        self.grid.addWidget(self.widgets.remove_button, 0, 3)
        self.grid.addLayout(disposition_layout, 0, 4)
        self.grid.addWidget(self.widgets.burn_in, 0, 5)
        self.grid.addLayout(self.init_language(sub_track), 0, 6)
        self.grid.addWidget(self.widgets.enable_check, 0, 8)

        self.setLayout(self.grid)
        self.check_dis_button()
        self.loading = False
        self.updating_burn = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(scaler.scale(17))
        self.widgets.up_button.setFixedHeight(scaler.scale(20))
        self.widgets.up_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(scaler.scale(17))
        self.widgets.down_button.setFixedHeight(scaler.scale(20))
        self.widgets.down_button.setIconSize(scaler.scale_size(12, 12))
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def init_language(self, sub_track: SubtitleTrack):
        self.widgets.language.addItems(language_list)
        self.widgets.language.setMaximumWidth(110)
        try:
            self.widgets.language.setCurrentIndex(language_list.index(Language(sub_track.language).name))
        except Exception:
            self.widgets.language.setCurrentIndex(language_list.index("English"))
        self.widgets.language.currentIndexChanged.connect(self.update_language)
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
        self.app.fastflix.current_video.subtitle_tracks[self.index].outdex = outdex
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText("[EXT]")

    @property
    def enabled(self):
        try:
            return self.app.fastflix.current_video.subtitle_tracks[self.index].enabled
        except IndexError:
            return False

    @property
    def language(self):
        return Language(self.widgets.language.currentText()).pt2b

    @property
    def burn_in(self):
        return self.widgets.burn_in.isChecked()

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
        sub_track.enabled = enabled
        self.widgets.track_number.setText("[EXT]" if enabled else "❌")
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
            self.parent.main.widgets.fast_time.setCurrentIndex(1)  # Set to "Exact"
        sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
        sub_track.burn_in = enable
        self.updating_burn = False
        self.page_update()

    def update_language(self):
        if not self.loading:
            sub_track = self.app.fastflix.current_video.subtitle_tracks[self.index]
            sub_track.language = self.language
            self.page_update()

    def page_update(self):
        if not self.loading:
            self.check_dis_button()
            return self.parent.main.page_update(build_thumbnail=False)

    def check_dis_button(self):
        track: SubtitleTrack = self.app.fastflix.current_video.subtitle_tracks[self.index]
        if any(track.dispositions.values()):
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=True))
        else:
            self.widgets.disposition.setStyleSheet(get_onyx_disposition_style(enabled=False))

    def remove(self):
        self.parent.remove_external_track(self)


class SubtitleList(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        top_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel(t("Subtitle Tracks"))
        label.setFixedHeight(30)
        top_layout.addWidget(label)
        top_layout.addStretch(1)

        self.add_subtitle_button = QtWidgets.QPushButton(t("Add External"))
        self.add_subtitle_button.setFixedWidth(150)
        self.add_subtitle_button.clicked.connect(self.add_external_subtitle)
        self.remove_all_button = QtWidgets.QPushButton(t("Unselect All"))
        self.remove_all_button.setFixedWidth(150)
        self.remove_all_button.clicked.connect(lambda: self.select_all(False))
        self.save_all_button = QtWidgets.QPushButton(t("Preserve All"))
        self.save_all_button.setFixedWidth(150)
        self.save_all_button.clicked.connect(lambda: self.select_all(True))

        top_layout.addWidget(self.add_subtitle_button)
        top_layout.addWidget(self.remove_all_button)
        top_layout.addWidget(self.save_all_button)

        super().__init__(app, parent, "Subtitle Tracks", "subtitle", top_row_layout=top_layout)
        self.main = parent.main
        self.app = app
        self._first_selected = False

    def select_all(self, select=True):
        for track in self.tracks:
            track.widgets.enable_check.setChecked(select)

    def add_external_subtitle(self):
        if not self.app.fastflix.current_video:
            return
        filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            caption=t("Select Subtitle File"),
            filter=f"{t('Subtitle Files')} (*.srt *.ass *.ssa *.vtt *.sup)",
        )
        if not filenames:
            return
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            sub_type = ext_subtitle_types.get(ext, "text")
            index = len(self.app.fastflix.current_video.subtitle_tracks)
            audio_end = len([x for x in self.app.fastflix.current_video.audio_tracks if x.enabled])
            self.app.fastflix.current_video.subtitle_tracks.append(
                SubtitleTrack(
                    index=0,
                    outdex=audio_end + index + 1,
                    burn_in=False,
                    language="",
                    subtitle_type=sub_type,
                    enabled=True,
                    long_name=f"[EXT] {Path(filename).name}",
                    external=True,
                    file_path=str(filename),
                )
            )
            new_widget = ExternalSubtitle(
                app=self.app,
                parent=self,
                index=index,
                first=False,
                enabled=True,
            )
            self.tracks.append(new_widget)
            self.inner_layout.addWidget(new_widget)
        self.reorder(update=True)

    def remove_external_track(self, widget):
        track_index = widget.index
        self.app.fastflix.current_video.subtitle_tracks.pop(track_index)
        self.tracks.remove(widget)
        widget.close()
        # Re-index all remaining widgets
        for i, w in enumerate(self.tracks):
            w.index = i
        self.reorder(update=True)

    def lang_match(self, track: Union[Subtitle, SubtitleTrack, dict], ignore_first=False):
        if not self.app.fastflix.config.opt("subtitle_select"):
            return False
        if isinstance(track, (Subtitle, SubtitleTrack)):
            language = track.language
        else:
            language = track.get("tags", {}).get("language", "")
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
            track_lang = Language(language)
        except InvalidLanguageValue:
            return True
        else:
            if Language(self.app.fastflix.config.opt("subtitle_language")) == track_lang:
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
        audio_end = len(self.app.fastflix.current_video.audio_tracks)
        for index, track in enumerate(self.app.fastflix.current_video.streams.subtitle):
            enabled = self.lang_match(track)
            subtitle_type = subtitle_types.get(track.get("codec_name", "text"), "text")
            self.app.fastflix.current_video.subtitle_tracks.append(
                SubtitleTrack(
                    index=track.index,
                    outdex=audio_end + index + 1,
                    dispositions={k: bool(v) for k, v in track.disposition.items()},
                    burn_in=False,
                    language=track.get("tags", {}).get("language", ""),
                    subtitle_type=subtitle_type,
                    enabled=enabled,
                    long_name=track.get("codec_long_name", f"{t('Subtitle Type')}:{subtitle_type}"),
                    raw_info=track,
                )
            )

            new_item = Subtitle(
                app=self.app,
                parent=self,
                index=index,
                first=True if index == 0 else False,
                enabled=enabled,
            )
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        if self.app.fastflix.config.opt("subtitle_automatic_burn_in"):
            first_default, first_forced = None, None
            for track in self.tracks:
                if (
                    not first_default
                    and self.app.fastflix.current_video.subtitle_tracks[track.index].dispositions.get("default", False)
                    and self.lang_match(track, ignore_first=True)
                ):
                    first_default = track
                    break
                if (
                    not first_forced
                    and self.app.fastflix.current_video.subtitle_tracks[track.index].dispositions.get("forced", False)
                    and self.lang_match(track, ignore_first=True)
                ):
                    first_forced = track
                    break
            if not self.app.fastflix.config.disable_automatic_subtitle_burn_in:
                if first_forced is not None:
                    first_forced.widgets.burn_in.setChecked(True)
                elif first_default is not None:
                    first_default.widgets.burn_in.setChecked(True)

        super()._new_source(self.tracks)

    def apply_profile_settings(self):
        """Re-apply subtitle filtering based on current profile settings."""
        self._first_selected = False

        for track in self.tracks:
            sub_track = self.app.fastflix.current_video.subtitle_tracks[track.index]
            enabled = self.lang_match(sub_track)
            sub_track.enabled = enabled
            track.widgets.enable_check.setChecked(enabled)

        if self.app.fastflix.config.opt("subtitle_automatic_burn_in"):
            # Reset any existing burn-in
            for track in self.tracks:
                track.widgets.burn_in.setChecked(False)

            first_default, first_forced = None, None
            for track in self.tracks:
                if (
                    not first_default
                    and self.app.fastflix.current_video.subtitle_tracks[track.index].dispositions.get("default", False)
                    and self.lang_match(track, ignore_first=True)
                ):
                    first_default = track
                    break
                if (
                    not first_forced
                    and self.app.fastflix.current_video.subtitle_tracks[track.index].dispositions.get("forced", False)
                    and self.lang_match(track, ignore_first=True)
                ):
                    first_forced = track
                    break
            if not self.app.fastflix.config.disable_automatic_subtitle_burn_in:
                if first_forced is not None:
                    first_forced.widgets.burn_in.setChecked(True)
                elif first_default is not None:
                    first_default.widgets.burn_in.setChecked(True)

        self.reorder(update=True)

    def reload(self, original_tracks):
        clear_list(self.tracks)

        for i, track in enumerate(self.app.fastflix.current_video.subtitle_tracks):
            if track.external:
                self.tracks.append(
                    ExternalSubtitle(
                        app=self.app,
                        parent=self,
                        index=i,
                        first=True if i == 0 else False,
                        enabled=track.enabled,
                    )
                )
            else:
                self.tracks.append(
                    Subtitle(
                        app=self.app,
                        parent=self,
                        index=i,
                        first=True if i == 0 else False,
                        enabled=track.enabled,
                    )
                )
        super()._new_source(self.tracks)

    def move_up(self, widget):
        self.app.fastflix.current_video.subtitle_tracks.insert(
            widget.index - 1, self.app.fastflix.current_video.subtitle_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index - 1, self.tracks.pop(index))
        self.reorder()

    def move_down(self, widget):
        self.app.fastflix.current_video.subtitle_tracks.insert(
            widget.index + 1, self.app.fastflix.current_video.subtitle_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index + 1, self.tracks.pop(index))
        self.reorder()
