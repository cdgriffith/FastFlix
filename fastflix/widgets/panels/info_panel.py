#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path

from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon
from fastflix.ui_styles import ONYX_COLORS

logger = logging.getLogger("fastflix")

COLUMNS_PER_ROW = 3

VIDEO_SECTIONS = [
    (
        "General",
        [
            ("index", "Index"),
            ("codec_name", "Codec"),
            ("codec_long_name", "Codec Full Name"),
            ("profile", "Profile"),
            ("level", "Level"),
            ("width", "Resolution"),
            ("r_frame_rate", "Frame Rate"),
            ("avg_frame_rate", "Avg Frame Rate"),
            ("duration", "Duration"),
            ("bit_rate", "Bit Rate"),
            ("nb_frames", "Frames"),
        ],
    ),
    (
        "Pixel Format",
        [
            ("pix_fmt", "Format"),
            ("bit_depth", "Bit Depth"),
            ("bits_per_raw_sample", "Bits/Raw Sample"),
            ("has_b_frames", "B-Frames"),
            ("field_order", "Field Order"),
            ("chroma_location", "Chroma"),
            ("sample_aspect_ratio", "Sample AR"),
            ("display_aspect_ratio", "Display AR"),
        ],
    ),
    (
        "Color",
        [
            ("color_range", "Range"),
            ("color_space", "Space"),
            ("color_transfer", "Transfer"),
            ("color_primaries", "Primaries"),
        ],
    ),
]

AUDIO_SECTIONS = [
    (
        "General",
        [
            ("index", "Index"),
            ("codec_name", "Codec"),
            ("codec_long_name", "Codec Full Name"),
            ("profile", "Profile"),
            ("sample_rate", "Sample Rate"),
            ("channels", "Channels"),
            ("channel_layout", "Layout"),
            ("sample_fmt", "Sample Fmt"),
            ("bit_rate", "Bit Rate"),
            ("duration", "Duration"),
            ("nb_frames", "Frames"),
            ("bits_per_sample", "Bits/Sample"),
        ],
    ),
]

SUBTITLE_SECTIONS = [
    (
        "General",
        [
            ("index", "Index"),
            ("codec_name", "Codec"),
            ("codec_long_name", "Codec Full Name"),
            ("duration", "Duration"),
        ],
    ),
]

DEFAULT_SECTIONS = [
    (
        "General",
        [
            ("index", "Index"),
            ("codec_name", "Codec"),
            ("codec_long_name", "Codec Full Name"),
            ("codec_type", "Type"),
        ],
    ),
]

SECTION_MAP = {
    "video": VIDEO_SECTIONS,
    "audio": AUDIO_SECTIONS,
    "subtitle": SUBTITLE_SECTIONS,
}

SPECIAL_KEYS = {"tags", "disposition", "side_data_list", "codec_type"}


def format_value(key, value, stream):
    if value is None or value == "":
        return ""
    if key == "bit_rate":
        try:
            bps = int(value)
            if bps >= 1_000_000:
                return f"{bps / 1_000_000:.2f} Mbps"
            return f"{bps / 1_000:.0f} kbps"
        except (ValueError, TypeError):
            return str(value)
    if key == "sample_rate":
        try:
            return f"{int(value) / 1_000:.1f} kHz"
        except (ValueError, TypeError):
            return str(value)
    if key in ("r_frame_rate", "avg_frame_rate"):
        try:
            if "/" in str(value):
                num, den = str(value).split("/")
                num, den = int(num), int(den)
                if den == 0:
                    return str(value)
                return f"{num / den:.3f} fps"
            return f"{float(value):.3f} fps"
        except (ValueError, TypeError, ZeroDivisionError):
            return str(value)
    if key == "duration":
        try:
            secs = float(value)
            minutes, secs = divmod(secs, 60)
            hours, minutes = divmod(int(minutes), 60)
            if hours:
                return f"{hours}:{minutes:02d}:{secs:06.3f}"
            return f"{int(minutes):02d}:{secs:06.3f}"
        except (ValueError, TypeError):
            return str(value)
    if key == "width":
        height = stream.get("height", "")
        return f"{value}x{height}" if height else str(value)
    if key == "channels":
        layout = stream.get("channel_layout", "")
        return f"{value} ({layout})" if layout else str(value)
    return str(value)


def build_section_group(title, fields, is_onyx):
    group = QtWidgets.QGroupBox(t(title))
    if is_onyx:
        group.setStyleSheet(
            f"QGroupBox {{ color: {ONYX_COLORS['text']}; border: 1px solid #666; border-radius: 4px; "
            f"margin-top: 8px; padding-top: 4px; }} "
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}"
        )
    grid = QtWidgets.QGridLayout()
    grid.setContentsMargins(8, 2, 8, 4)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(2)
    row = 0
    col = 0
    for label_text, value_text in fields:
        key_label = QtWidgets.QLabel(f"<b>{label_text}:</b>")
        val_label = QtWidgets.QLabel(str(value_text))
        val_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(key_label, row, col * 2)
        grid.addWidget(val_label, row, col * 2 + 1)
        col += 1
        if col >= COLUMNS_PER_ROW:
            col = 0
            row += 1
    # Spread columns evenly across full width
    for c in range(COLUMNS_PER_ROW):
        grid.setColumnStretch(c * 2 + 1, 1)
    group.setLayout(grid)
    return group


def build_stream_widget(stream, parent, theme):
    codec_type = stream.get("codec_type", "")
    sections = SECTION_MAP.get(codec_type, DEFAULT_SECTIONS)
    is_onyx = theme.lower() in ("dark", "onyx")

    shown_keys = set(SPECIAL_KEYS)
    if codec_type == "video":
        shown_keys.add("height")
    if codec_type == "audio":
        shown_keys.add("channel_layout")

    scroll = QtWidgets.QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(4)

    # Defined sections
    for section_name, field_defs in sections:
        fields = []
        for key, label in field_defs:
            shown_keys.add(key)
            value = stream.get(key)
            if value is None or str(value) == "":
                continue
            fields.append((t(label), format_value(key, value, stream)))
        if fields:
            layout.addWidget(build_section_group(section_name, fields, is_onyx))

    # Tags
    tags = stream.get("tags", {})
    if tags:
        fields = [(k.replace("_", " ").title(), str(v)) for k, v in tags.items()]
        layout.addWidget(build_section_group("Tags", fields, is_onyx))

    # Disposition - only truthy values
    disposition = stream.get("disposition", {})
    active = [(k.replace("_", " ").title(), t("Yes")) for k, v in disposition.items() if v]
    if active:
        layout.addWidget(build_section_group("Disposition", active, is_onyx))

    # Side Data / HDR
    side_data = stream.get("side_data_list", [])
    if side_data:
        for entry in side_data:
            if not isinstance(entry, dict):
                continue
            side_type = entry.get("side_data_type", t("Unknown"))
            fields = [(k.replace("_", " ").title(), str(v)) for k, v in entry.items() if k != "side_data_type"]
            if fields:
                layout.addWidget(build_section_group(side_type, fields, is_onyx))

    # Other - remaining keys
    other_fields = []
    for key in stream.keys():
        if key in shown_keys:
            continue
        value = stream.get(key)
        if value is None or str(value) == "" or isinstance(value, (dict, list)):
            continue
        other_fields.append((key.replace("_", " ").title(), format_value(key, value, stream)))
    if other_fields:
        layout.addWidget(build_section_group("Other", other_fields, is_onyx))

    layout.addStretch()
    container.setLayout(layout)

    # Calculate the natural content size so the scroll area never squishes it
    content_size = layout.sizeHint()
    container.setMinimumSize(content_size)

    scroll.setWidget(container)
    return scroll


class InfoPanel(QtWidgets.QTabWidget):
    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.attachments = Box()

        self.download_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-save", self.app.fastflix.config.theme)), t("Download JSON")
        )
        self.download_button.setToolTip(t("Download JSON"))
        self.download_button.clicked.connect(self.save_json)
        self.setCornerWidget(self.download_button, QtCore.Qt.Corner.TopRightCorner)

    def reset(self):
        for i in range(self.count() - 1, -1, -1):
            self.removeTab(i)

        if not self.app.fastflix.current_video:
            return

        all_stream = []
        for x in self.app.fastflix.current_video.streams.values():
            all_stream.extend(x)

        theme = self.app.fastflix.config.theme
        max_content_height = 0
        for stream in sorted(all_stream, key=lambda z: z["index"]):
            widget = build_stream_widget(stream, self, theme)
            self.addTab(widget, f"{stream['index']}: {stream['codec_type'].title()} ({stream.get('codec_name', '')})")
            inner = widget.widget()
            if inner:
                max_content_height = max(max_content_height, inner.minimumSizeHint().height())

        if max_content_height > 0:
            tab_bar_height = self.tabBar().sizeHint().height()
            self.setMinimumHeight(max_content_height + tab_bar_height + 16)

    def save_json(self):
        if not self.app.fastflix.current_video:
            return

        all_streams = []
        for x in self.app.fastflix.current_video.streams.values():
            all_streams.extend(x)
        all_streams.sort(key=lambda z: z["index"])

        data = {"streams": [Box(s).to_dict() for s in all_streams]}
        if self.app.fastflix.current_video.format:
            data["format"] = Box(self.app.fastflix.current_video.format).to_dict()

        source_name = self.app.fastflix.current_video.source.stem
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption=t("Download JSON"),
            dir=str(Path("~").expanduser() / f"{source_name}_info.json"),
            filter=f"{t('JSON Files')} (*.json)",
        )
        if filename and filename[0]:
            try:
                Path(filename[0]).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            except Exception:
                logger.exception("Failed to save JSON")
