#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
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


def load_history(data_path: Path) -> list[HistoryEntry]:
    history_file = get_history_file(data_path)
    if not history_file.exists():
        return []
    try:
        data = Box.from_yaml(filename=history_file)
    except Exception:
        logger.exception("Failed to load history file")
        return []
    entries = []
    for item in data.get("entries", []):
        try:
            entries.append(HistoryEntry(**item))
        except Exception:
            logger.warning(f"Skipping invalid history entry: {item}")
    return entries


def save_history(data_path: Path, entries: list[HistoryEntry]):
    history_file = get_history_file(data_path)
    try:
        data = Box(entries=[e.model_dump() for e in entries])
        data.to_yaml(filename=history_file, default_flow_style=False)
    except Exception:
        logger.exception("Failed to save history file")


def add_history_entry(data_path: Path, entry: HistoryEntry, max_items: int = DEFAULT_MAX_HISTORY):
    entries = load_history(data_path)
    entries.append(entry)
    if max_items > 0 and len(entries) > max_items:
        removed = entries[: len(entries) - max_items]
        entries = entries[len(entries) - max_items :]
        thumbs_dir = get_history_thumbnails_dir(data_path)
        for old_entry in removed:
            if old_entry.thumbnail_filename:
                thumb_path = thumbs_dir / old_entry.thumbnail_filename
                thumb_path.unlink(missing_ok=True)
    save_history(data_path, entries)


def trim_history(data_path: Path, max_items: int):
    """Trim history to max_items, removing oldest entries. Negative means unlimited."""
    if max_items <= 0:
        return
    entries = load_history(data_path)
    if len(entries) <= max_items:
        return
    removed = entries[: len(entries) - max_items]
    entries = entries[len(entries) - max_items :]
    thumbs_dir = get_history_thumbnails_dir(data_path)
    for old_entry in removed:
        if old_entry.thumbnail_filename:
            (thumbs_dir / old_entry.thumbnail_filename).unlink(missing_ok=True)
    save_history(data_path, entries)


def delete_history_entry(data_path: Path, uuid: str):
    entries = load_history(data_path)
    thumbs_dir = get_history_thumbnails_dir(data_path)
    entries_new = []
    for entry in entries:
        if entry.uuid == uuid:
            if entry.thumbnail_filename:
                (thumbs_dir / entry.thumbnail_filename).unlink(missing_ok=True)
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
