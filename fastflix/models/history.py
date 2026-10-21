#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
import tempfile
from pathlib import Path
from box import Box
from pydantic import BaseModel, Field

logger = logging.getLogger("fastflix")

DEFAULT_MAX_HISTORY = 50

HISTORY_MAX_OPTIONS = {
    "10": 10,
    "20": 20,
    "50": 50,
    "100": 100,
    "Unlimited": -1,
}


class HistoryEntry(BaseModel):
    uuid: str
    source: str
    output: str
    encoder_name: str
    encoder_settings_summary: str = ""
    encoder_settings: dict = Field(default_factory=dict)
    audio_summary: str = ""
    subtitle_summary: str = ""
    resolution: str = ""
    duration: float = 0.0
    file_size: int = 0
    completed_at: str = ""
    thumbnail_filename: str = ""
    success: bool = True
    encode_duration_secs: float = 0.0


def get_history_file(data_path: Path) -> Path:
    return data_path / "history.yaml"


def get_history_thumbnails_dir(data_path: Path) -> Path:
    return data_path / "history_thumbnails"


class HistoryLoadError(Exception):
    pass


def load_history_strict(data_path: Path) -> list[HistoryEntry]:
    """Like load_history, but raises HistoryLoadError if an existing history file cannot be read."""
    history_file = get_history_file(data_path)
    if not history_file.exists():
        return []
    try:
        data = Box.from_yaml(filename=history_file)
    except Exception as err:
        raise HistoryLoadError(f"Failed to load history file {history_file}: {err}") from err
    entries = []
    for item in data.get("entries", []):
        try:
            entries.append(HistoryEntry(**item))
        except Exception:
            logger.warning(f"Skipping invalid history entry: {item}")
    return entries


def load_history(data_path: Path) -> list[HistoryEntry]:
    try:
        return load_history_strict(data_path)
    except HistoryLoadError:
        logger.exception("Failed to load history file")
        return []


def save_history(data_path: Path, entries: list[HistoryEntry]):
    history_file = get_history_file(data_path)
    temp_path = None
    try:
        data = Box(entries=[e.model_dump() for e in entries])
        history_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(suffix=".yaml.tmp", prefix="history_", dir=history_file.parent)
        os.close(fd)
        data.to_yaml(filename=temp_path, default_flow_style=False)
        os.replace(temp_path, history_file)
    except Exception:
        logger.exception("Failed to save history file")
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _delete_thumbnail(thumbs_dir: Path, filename: str):
    if not filename:
        return
    name = Path(filename).name
    if not name or name in (".", ".."):
        return
    thumb_path = thumbs_dir / name
    try:
        if thumb_path.resolve().parent != thumbs_dir.resolve():
            logger.warning(f"Refusing to delete history thumbnail outside of {thumbs_dir}: {filename}")
            return
        thumb_path.unlink(missing_ok=True)
    except OSError:
        logger.exception(f"Could not delete history thumbnail {thumb_path}")


def _load_for_update(data_path: Path) -> list[HistoryEntry] | None:
    try:
        return load_history_strict(data_path)
    except HistoryLoadError:
        logger.exception("History file is unreadable, not modifying it to avoid losing existing history")
        return None


def add_history_entry(data_path: Path, entry: HistoryEntry, max_items: int = DEFAULT_MAX_HISTORY):
    entries = _load_for_update(data_path)
    if entries is None:
        return
    entries.append(entry)
    if max_items > 0 and len(entries) > max_items:
        removed = entries[: len(entries) - max_items]
        entries = entries[len(entries) - max_items :]
        thumbs_dir = get_history_thumbnails_dir(data_path)
        for old_entry in removed:
            _delete_thumbnail(thumbs_dir, old_entry.thumbnail_filename)
    save_history(data_path, entries)


def trim_history(data_path: Path, max_items: int):
    """Trim history to max_items, removing oldest entries. Negative means unlimited."""
    if max_items <= 0:
        return
    entries = _load_for_update(data_path)
    if entries is None or len(entries) <= max_items:
        return
    removed = entries[: len(entries) - max_items]
    entries = entries[len(entries) - max_items :]
    thumbs_dir = get_history_thumbnails_dir(data_path)
    for old_entry in removed:
        _delete_thumbnail(thumbs_dir, old_entry.thumbnail_filename)
    save_history(data_path, entries)


def delete_history_entry(data_path: Path, uuid: str):
    entries = _load_for_update(data_path)
    if entries is None:
        return
    thumbs_dir = get_history_thumbnails_dir(data_path)
    entries_new = []
    for entry in entries:
        if entry.uuid == uuid:
            _delete_thumbnail(thumbs_dir, entry.thumbnail_filename)
        else:
            entries_new.append(entry)
    save_history(data_path, entries_new)


def clear_history(data_path: Path):
    history_file = get_history_file(data_path)
    history_file.unlink(missing_ok=True)
    thumbs_dir = get_history_thumbnails_dir(data_path)
    if thumbs_dir.exists():
        shutil.rmtree(thumbs_dir, ignore_errors=True)


def build_settings_summary(encoder_settings: dict) -> str:
    """Extract key settings into a human-readable summary string."""
    parts = []
    # Quality settings
    for key in ("crf", "qp", "cqp", "q", "qscale"):
        if key in encoder_settings and encoder_settings[key] is not None:
            parts.append(f"{key.upper()}={encoder_settings[key]}")
            break
    # Bitrate
    if encoder_settings.get("bitrate"):
        parts.append(f"Bitrate={encoder_settings['bitrate']}")
    # Preset/speed
    for key in ("preset", "speed"):
        if key in encoder_settings and encoder_settings[key] not in (None, "default", ""):
            parts.append(f"{key.capitalize()}={encoder_settings[key]}")
            break
    # Profile
    if encoder_settings.get("profile") and encoder_settings["profile"] not in ("default", "auto", "Auto"):
        parts.append(f"Profile={encoder_settings['profile']}")
    return ", ".join(parts) if parts else "Default settings"
