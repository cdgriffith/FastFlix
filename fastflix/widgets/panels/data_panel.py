#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from box import Box
from PySide6 import QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.encode import DataTrack
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon
from fastflix.shared import no_border, shrink_text_to_fit
from fastflix.ui_scale import scaler
from fastflix.widgets.panels.abstract_list import FlixList

logger = logging.getLogger("fastflix")

COVER_NAMES = {"cover", "small_cover", "cover_land", "small_cover_land"}

# Container support for data/attachment streams
# MKV supports everything; MP4/M4V support timecodes but not font attachments
NO_DATA_EXTENSIONS = {".gif", ".webm", ".webp", ".avif"}
NO_ATTACHMENT_EXTENSIONS = {".gif", ".webm", ".webp", ".avif", ".mp4", ".m4v", ".mov", ".ts", ".mts", ".m2ts"}


class DataTrackWidget(QtWidgets.QTabWidget):
    def __init__(self, app, parent, index, enabled=True, first=False):
        self.loading = True
        super(DataTrackWidget, self).__init__(parent)
        self.app = app
        self.parent = parent
        self.setObjectName("DataTrack")
        self.index = index
        self.outdex = None
        self.first = first
        self.last = False

        track: DataTrack = self.app.fastflix.current_video.data_tracks[index]

        # Determine type badge text
        if track.codec_type == "attachment":
            type_badge = t("Font") if track.mimetype and "font" in track.mimetype.lower() else t("Attachment")
        else:
            type_badge = t("Data")

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{track.index}:{track.outdex}" if enabled else "❌"),
            info_label=QtWidgets.QLabel(f"  {track.friendly_info}"),
            type_badge=QtWidgets.QLabel(type_badge),
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            enable_check=QtWidgets.QCheckBox(t("Preserve")),
        )

        self.widgets.up_button.setStyleSheet(no_border)
        self.widgets.down_button.setStyleSheet(no_border)

        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)

        self.setFixedHeight(60)

        # Tooltip with raw info
        if track.raw_info:
            try:
                self.widgets.info_label.setToolTip(Box(track.raw_info).to_yaml())
            except Exception:
                self.widgets.info_label.setToolTip(str(track.raw_info))

        # Check container compatibility
        self._check_compatibility(track)

        self.grid = QtWidgets.QGridLayout()
        self.grid.addLayout(self.init_move_buttons(), 0, 0)
        self.grid.addWidget(self.widgets.track_number, 0, 1)
        self.grid.addWidget(self.widgets.info_label, 0, 2)
        self.grid.setColumnStretch(2, True)
        self.grid.addWidget(self.widgets.type_badge, 0, 3)
        self.grid.addWidget(self.widgets.enable_check, 0, 4)

        self.setLayout(self.grid)
        self.loading = False

    def _check_compatibility(self, track: DataTrack):
        output_path = self.app.fastflix.current_video.video_settings.output_path
        if not output_path:
            return
        ext = str(output_path).rsplit(".", 1)[-1].lower() if "." in str(output_path) else ""
        ext_with_dot = f".{ext}"

        incompatible = False
        reason = ""

        if track.codec_type == "data" and ext_with_dot in NO_DATA_EXTENSIONS:
            incompatible = True
            reason = t("Data streams are not supported in this output format")
        elif track.codec_type == "attachment" and ext_with_dot in NO_ATTACHMENT_EXTENSIONS:
            incompatible = True
            reason = t("Attachment streams are not supported in this output format")

        if incompatible:
            self.widgets.enable_check.setChecked(False)
            self.widgets.enable_check.setEnabled(False)
            self.widgets.enable_check.setToolTip(reason)
            track.enabled = False

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

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def set_outdex(self, outdex):
        self.app.fastflix.current_video.data_tracks[self.index].outdex = outdex
        track: DataTrack = self.app.fastflix.current_video.data_tracks[self.index]
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{track.index}:{track.outdex}")

    @property
    def enabled(self):
        try:
            return self.app.fastflix.current_video.data_tracks[self.index].enabled
        except IndexError:
            return False

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        track = self.app.fastflix.current_video.data_tracks[self.index]
        track.enabled = enabled
        self.widgets.track_number.setText(f"{track.index}:{track.outdex}" if enabled else "❌")
        self.parent.reorder(update=True)

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class DataList(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        top_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel(t("Data & Attachments"))
        label.setFixedHeight(30)
        top_layout.addWidget(label)
        top_layout.addStretch(1)

        self.remove_all_button = QtWidgets.QPushButton(t("Unselect All"))
        self.remove_all_button.setFixedWidth(150)
        self.remove_all_button.clicked.connect(lambda: self.select_all(False))
        self.save_all_button = QtWidgets.QPushButton(t("Preserve All"))
        self.save_all_button.setFixedWidth(150)
        self.save_all_button.clicked.connect(lambda: self.select_all(True))

        for w in (self.remove_all_button, self.save_all_button):
            shrink_text_to_fit(w)

        top_layout.addWidget(self.remove_all_button)
        top_layout.addWidget(self.save_all_button)

        super().__init__(app, parent, "Data & Attachments", "data", top_row_layout=top_layout)
        self.main = parent.main
        self.app = app

    def select_all(self, select=True):
        for track in self.tracks:
            if track.widgets.enable_check.isEnabled():
                track.widgets.enable_check.setChecked(select)

    @staticmethod
    def _get_name_tags(stream):
        """Return a display string for any tags containing 'name' in their key."""
        tags = stream.get("tags", {})
        parts = []
        for key, value in tags.items():
            if "name" in key.lower() and value:
                parts.append(f"{key}: {value}")
        return ", ".join(parts)

    def _is_cover_attachment(self, stream):
        """Check if an attachment stream is a cover image (handled by cover panel)."""
        filename = stream.get("tags", {}).get("filename", "")
        mimetype = stream.get("tags", {}).get("mimetype", "")
        base_name = filename.rsplit(".", 1)[0].lower() if filename else ""
        if base_name in COVER_NAMES:
            return True
        if mimetype.startswith("image"):
            return True
        return False

    def new_source(self):
        self.tracks = []
        video = self.app.fastflix.current_video
        video.data_tracks = []

        # Add data streams
        for stream in getattr(video.streams, "data", []):
            codec_name = stream.get("codec_name", "")
            codec_long_name = stream.get("codec_long_name", codec_name)
            codec_tag_string = stream.get("codec_tag_string", "")
            title = stream.get("tags", {}).get("title", "")
            friendly = codec_long_name or codec_name
            if codec_tag_string:
                friendly = f"{friendly} [{codec_tag_string}]"
            if title:
                friendly = f"{title} ({friendly})"
            name_tags = self._get_name_tags(stream)
            if name_tags:
                friendly = f"{friendly} - {name_tags}"

            video.data_tracks.append(
                DataTrack(
                    index=stream.index,
                    outdex=0,
                    enabled=True,
                    codec_name=codec_name,
                    codec_type="data",
                    title=title,
                    friendly_info=friendly,
                    raw_info=stream,
                )
            )

        # Add non-image attachment streams (fonts, etc.)
        for stream in getattr(video.streams, "attachment", []):
            if self._is_cover_attachment(stream):
                continue
            codec_name = stream.get("codec_name", "")
            codec_tag_string = stream.get("codec_tag_string", "")
            filename = stream.get("tags", {}).get("filename", "")
            mimetype = stream.get("tags", {}).get("mimetype", "")
            friendly = filename if filename else codec_name
            if codec_tag_string:
                friendly = f"{friendly} [{codec_tag_string}]"
            if mimetype:
                friendly = f"{friendly} ({mimetype})"
            name_tags = self._get_name_tags(stream)
            if name_tags:
                friendly = f"{friendly} - {name_tags}"

            video.data_tracks.append(
                DataTrack(
                    index=stream.index,
                    outdex=0,
                    enabled=True,
                    codec_name=codec_name,
                    codec_type="attachment",
                    filename=filename,
                    mimetype=mimetype,
                    friendly_info=friendly,
                    raw_info=stream,
                )
            )

        for i, track in enumerate(video.data_tracks):
            new_item = DataTrackWidget(
                app=self.app,
                parent=self,
                index=i,
                first=True if i == 0 else False,
                enabled=track.enabled,
            )
            self.tracks.append(new_item)

        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        super()._new_source(self.tracks)

    def apply_profile_settings(self, profile):
        """Apply profile data passthrough settings to data tracks."""
        if profile.data_passthrough is False:
            self.select_all(False)
        else:
            self.select_all(True)

    def get_settings(self):
        # Widget state is already written to data_tracks via set_outdex / update_enable
        pass

    def reload(self, data_tracks):
        from fastflix.shared import clear_list

        clear_list(self.tracks)

        for i, track in enumerate(self.app.fastflix.current_video.data_tracks):
            self.tracks.append(
                DataTrackWidget(
                    app=self.app,
                    parent=self,
                    index=i,
                    first=True if i == 0 else False,
                    enabled=track.enabled,
                )
            )
        super()._new_source(self.tracks)

    def move_up(self, widget):
        self.app.fastflix.current_video.data_tracks.insert(
            widget.index - 1, self.app.fastflix.current_video.data_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index - 1, self.tracks.pop(index))
        self.reorder()

    def move_down(self, widget):
        self.app.fastflix.current_video.data_tracks.insert(
            widget.index + 1, self.app.fastflix.current_video.data_tracks.pop(widget.index)
        )
        index = self.tracks.index(widget)
        self.tracks.insert(index + 1, self.tracks.pop(index))
        self.reorder()
