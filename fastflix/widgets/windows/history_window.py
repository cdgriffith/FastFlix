# -*- coding: utf-8 -*-
import logging
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.history import (
    HISTORY_MAX_OPTIONS,
    HistoryEntry,
    load_history,
    clear_history,
    delete_history_entry,
    get_history_thumbnails_dir,
    trim_history,
)
from fastflix.shared import yes_no_message

logger = logging.getLogger("fastflix")


class ElidedLabel(QtWidgets.QLabel):
    """A QLabel that elides text with an ellipsis when it doesn't fit."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setMinimumWidth(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

    def setText(self, text):
        self._full_text = text
        super().setText(text)
        self.update()

    def resizeEvent(self, event):
        self._update_elided_text()
        super().resizeEvent(event)

    def _update_elided_text(self):
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, QtCore.Qt.ElideRight, self.width())
        super().setText(elided)


def _format_encode_duration(seconds: float) -> str:
    """Format encode duration into a human-readable string."""
    if seconds <= 0:
        return ""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


class HistoryItemWidget(QtWidgets.QFrame):
    apply_settings_signal = QtCore.Signal(HistoryEntry)
    delete_signal = QtCore.Signal(str)

    def __init__(self, entry: HistoryEntry, thumbnails_dir: Path, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame { margin: 2px; padding: 4px; }")
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Collapsed row
        collapsed_layout = QtWidgets.QHBoxLayout()

        # Thumbnail
        thumb_label = QtWidgets.QLabel()
        thumb_label.setFixedSize(120, 68)
        thumb_label.setAlignment(QtCore.Qt.AlignCenter)
        thumb_label.setStyleSheet("background-color: #222;")
        thumb_path = thumbnails_dir / entry.thumbnail_filename if entry.thumbnail_filename else None
        if thumb_path and thumb_path.exists():
            pixmap = QtGui.QPixmap(str(thumb_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 68, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            thumb_label.setPixmap(pixmap)
        else:
            thumb_label.setText(t("No Preview"))
            thumb_label.setAlignment(QtCore.Qt.AlignCenter)
            thumb_label.setStyleSheet("background-color: #333; color: #888;")
        collapsed_layout.addWidget(thumb_label)

        # Info section
        info_layout = QtWidgets.QVBoxLayout()
        source_name = Path(entry.source).name
        output_name = Path(entry.output).name

        source_label = ElidedLabel(source_name)
        bold_font = source_label.font()
        bold_font.setBold(True)
        source_label.setFont(bold_font)
        source_label.setToolTip(entry.source)
        info_layout.addWidget(source_label)

        output_label = ElidedLabel(f"\u2192 {output_name}")
        output_label.setToolTip(entry.output)
        output_label.setStyleSheet("color: #aaa;")
        info_layout.addWidget(output_label)

        summary_text = f"{entry.encoder_name}"
        if entry.encoder_settings_summary:
            summary_text += f" \u2014 {entry.encoder_settings_summary}"
        summary_label = ElidedLabel(summary_text)
        summary_label.setToolTip(summary_text)
        info_layout.addWidget(summary_label)

        # Status + date + encode time line
        meta_parts = []
        if entry.success:
            meta_parts.append("Success")
        else:
            meta_parts.append("Failed")
        if entry.resolution:
            meta_parts.append(entry.resolution)
        encode_dur = _format_encode_duration(entry.encode_duration_secs)
        if encode_dur:
            meta_parts.append(f"Encode time: {encode_dur}")
        date_text = entry.completed_at[:19].replace("T", " ") if entry.completed_at else ""
        if date_text:
            meta_parts.append(date_text)
        meta_label = ElidedLabel(" | ".join(meta_parts))
        status_color = "#4CAF50" if entry.success else "#F44336"
        meta_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        info_layout.addWidget(meta_label)

        collapsed_layout.addLayout(info_layout, stretch=1)

        # Buttons
        button_layout = QtWidgets.QVBoxLayout()
        apply_button = QtWidgets.QPushButton(t("Apply Settings"))
        apply_button.setFixedWidth(110)
        apply_button.clicked.connect(lambda: self.apply_settings_signal.emit(self.entry))
        button_layout.addWidget(apply_button)

        self.details_button = QtWidgets.QPushButton(t("Details"))
        self.details_button.setFixedWidth(110)
        self.details_button.setCheckable(True)
        self.details_button.clicked.connect(self._toggle_details)
        button_layout.addWidget(self.details_button)

        delete_button = QtWidgets.QPushButton(t("Delete"))
        delete_button.setFixedWidth(110)
        delete_button.setStyleSheet("QPushButton { color: #F44336; }")
        delete_button.clicked.connect(lambda: self.delete_signal.emit(self.entry.uuid))
        button_layout.addWidget(delete_button)
        button_layout.addStretch()

        collapsed_layout.addLayout(button_layout)
        main_layout.addLayout(collapsed_layout)

        # Details section (hidden by default)
        self.details_frame = QtWidgets.QFrame()
        self.details_frame.setVisible(False)
        details_layout = QtWidgets.QVBoxLayout()
        details_layout.setContentsMargins(8, 4, 8, 4)

        # Encoder settings — one per line for readability
        if entry.encoder_settings:
            details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('Encoder Settings')}:</b>"))
            for k, v in entry.encoder_settings.items():
                if v is not None and k != "name":
                    setting_label = QtWidgets.QLabel(f"    {k}: {v}")
                    setting_label.setStyleSheet("font-family: monospace; color: #ccc;")
                    details_layout.addWidget(setting_label)

        if entry.audio_summary:
            details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('Audio')}:</b> {entry.audio_summary}"))
        if entry.subtitle_summary:
            details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('Subtitles')}:</b> {entry.subtitle_summary}"))
        if entry.duration:
            minutes = int(entry.duration // 60)
            seconds = int(entry.duration % 60)
            details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('Duration')}:</b> {minutes}m {seconds}s"))
        if entry.file_size:
            size_mb = entry.file_size / (1024 * 1024)
            if size_mb >= 1024:
                details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('File Size')}:</b> {size_mb / 1024:.2f} GB"))
            else:
                details_layout.addWidget(QtWidgets.QLabel(f"<b>{t('File Size')}:</b> {size_mb:.1f} MB"))

        self.details_frame.setLayout(details_layout)
        main_layout.addWidget(self.details_frame)

        self.setLayout(main_layout)

    def _toggle_details(self):
        self.details_frame.setVisible(self.details_button.isChecked())


class HistoryWindow(QtWidgets.QWidget):
    apply_settings_requested = QtCore.Signal(HistoryEntry)

    def __init__(self, app, parent=None):
        super().__init__(None)
        self.app = app
        self.setWindowTitle(t("Encoding History"))
        self.setMinimumSize(1000, 500)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)

        layout = QtWidgets.QVBoxLayout()

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(f"<h2>{t('Encoding History')}</h2>")
        header_layout.addWidget(title)
        header_layout.addStretch()

        header_layout.addWidget(QtWidgets.QLabel(t("Max items") + ":"))
        self.max_items_combo = QtWidgets.QComboBox()
        self.max_items_combo.addItems(list(HISTORY_MAX_OPTIONS.keys()))
        # Set current from config
        current_max = self.app.fastflix.config.history_max_items
        for label, value in HISTORY_MAX_OPTIONS.items():
            if value == current_max:
                self.max_items_combo.setCurrentText(label)
                break
        self.max_items_combo.currentTextChanged.connect(self._max_items_changed)
        header_layout.addWidget(self.max_items_combo)

        clear_button = QtWidgets.QPushButton(t("Clear History"))
        clear_button.clicked.connect(self._clear_history)
        header_layout.addWidget(clear_button)
        layout.addLayout(header_layout)

        # Scroll area with history items
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll_widget.setLayout(self.scroll_layout)
        scroll.setWidget(self.scroll_widget)
        layout.addWidget(scroll)

        self.setLayout(layout)
        self._load_entries()

    def _load_entries(self):
        # Clear existing items
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = load_history(self.app.fastflix.data_path)
        thumbnails_dir = get_history_thumbnails_dir(self.app.fastflix.data_path)

        if not entries:
            empty_label = QtWidgets.QLabel(t("No encoding history yet."))
            empty_label.setAlignment(QtCore.Qt.AlignCenter)
            empty_label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
            self.scroll_layout.addWidget(empty_label)
            return

        # Most recent first
        for entry in reversed(entries):
            widget = HistoryItemWidget(entry, thumbnails_dir)
            widget.apply_settings_signal.connect(self.apply_settings_requested.emit)
            widget.delete_signal.connect(self._delete_entry)
            self.scroll_layout.addWidget(widget)

    def _max_items_changed(self, text: str):
        new_max = HISTORY_MAX_OPTIONS.get(text, 50)
        self.app.fastflix.config.history_max_items = new_max
        self.app.fastflix.config.save()
        if new_max > 0:
            trim_history(self.app.fastflix.data_path, new_max)
            self._load_entries()

    def _delete_entry(self, uuid: str):
        delete_history_entry(self.app.fastflix.data_path, uuid)
        self._load_entries()

    def _clear_history(self):
        if yes_no_message(
            t("Are you sure you want to delete all encoding history?"),
            title=t("Clear History"),
        ):
            clear_history(self.app.fastflix.data_path)
            self._load_entries()
