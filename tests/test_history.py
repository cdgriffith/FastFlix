#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from fastflix.models.history import (
    HistoryEntry,
    add_history_entry,
    build_settings_summary,
    clear_history,
    get_history_file,
    get_history_thumbnails_dir,
    load_history,
    save_history,
    trim_history,
)


@pytest.fixture
def tmp_data_path(tmp_path):
    return tmp_path


def _make_entry(**overrides):
    defaults = {
        "uuid": "test-uuid-1234",
        "source": "/videos/input.mkv",
        "output": "/videos/output.mkv",
        "encoder_name": "HEVC (x265)",
        "encoder_settings_summary": "CRF=22, Preset=medium",
        "encoder_settings": {"crf": 22, "preset": "medium", "name": "HEVC (x265)"},
        "audio_summary": "English (aac)",
        "subtitle_summary": "",
        "resolution": "1920x1080",
        "duration": 120.5,
        "file_size": 50_000_000,
        "completed_at": "2026-03-11T10:00:00",
        "thumbnail_filename": "test-uuid-1234.jpg",
    }
    defaults.update(overrides)
    return HistoryEntry(**defaults)


def test_history_entry_creation():
    entry = _make_entry()
    assert entry.uuid == "test-uuid-1234"
    assert entry.encoder_name == "HEVC (x265)"
    assert entry.file_size == 50_000_000


def test_save_and_load_history(tmp_data_path):
    entries = [_make_entry(uuid="a"), _make_entry(uuid="b")]
    save_history(tmp_data_path, entries)

    loaded = load_history(tmp_data_path)
    assert len(loaded) == 2
    assert loaded[0].uuid == "a"
    assert loaded[1].uuid == "b"


def test_add_history_entry(tmp_data_path):
    add_history_entry(tmp_data_path, _make_entry(uuid="first"))
    add_history_entry(tmp_data_path, _make_entry(uuid="second"))

    loaded = load_history(tmp_data_path)
    assert len(loaded) == 2
    assert loaded[0].uuid == "first"
    assert loaded[1].uuid == "second"


def test_load_history_empty(tmp_data_path):
    loaded = load_history(tmp_data_path)
    assert loaded == []


def test_clear_history(tmp_data_path):
    add_history_entry(tmp_data_path, _make_entry())

    # Create thumbnails dir with a file
    thumbs_dir = get_history_thumbnails_dir(tmp_data_path)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    (thumbs_dir / "test.jpg").write_text("fake")

    clear_history(tmp_data_path)

    assert not get_history_file(tmp_data_path).exists()
    assert not thumbs_dir.exists()


def test_history_trimming(tmp_data_path):
    """Test that history is trimmed to max_items."""
    max_items = 20
    for i in range(max_items + 5):
        add_history_entry(tmp_data_path, _make_entry(uuid=f"entry-{i}"), max_items=max_items)

    loaded = load_history(tmp_data_path)
    assert len(loaded) == max_items
    assert loaded[0].uuid == "entry-5"
    assert loaded[-1].uuid == f"entry-{max_items + 4}"


def test_history_unlimited(tmp_data_path):
    """Test that max_items=-1 means unlimited."""
    for i in range(60):
        add_history_entry(tmp_data_path, _make_entry(uuid=f"entry-{i}"), max_items=-1)

    loaded = load_history(tmp_data_path)
    assert len(loaded) == 60


def test_build_settings_summary_crf():
    result = build_settings_summary({"crf": 22, "preset": "slow", "profile": "main"})
    assert "CRF=22" in result
    assert "Preset=slow" in result
    assert "Profile=main" in result


def test_build_settings_summary_bitrate():
    result = build_settings_summary({"bitrate": "5000k", "preset": "medium"})
    assert "Bitrate=5000k" in result
    assert "Preset=medium" in result


def test_build_settings_summary_qp():
    result = build_settings_summary({"qp": 26, "speed": "4"})
    assert "QP=26" in result
    assert "Speed=4" in result


def test_build_settings_summary_default():
    result = build_settings_summary({"name": "Copy"})
    assert result == "Default settings"


def test_build_settings_summary_skips_defaults():
    result = build_settings_summary({"preset": "default", "profile": "auto"})
    assert "Profile" not in result


def test_history_entry_success_default():
    entry = _make_entry()
    assert entry.success is True
    assert entry.encode_duration_secs == 0.0


def test_history_entry_failed():
    entry = _make_entry(success=False, encode_duration_secs=123.4)
    assert entry.success is False
    assert entry.encode_duration_secs == 123.4


def test_save_and_load_preserves_new_fields(tmp_data_path):
    entry = _make_entry(success=False, encode_duration_secs=300.5)
    add_history_entry(tmp_data_path, entry)

    loaded = load_history(tmp_data_path)
    assert len(loaded) == 1
    assert loaded[0].success is False
    assert loaded[0].encode_duration_secs == 300.5


def test_trim_history(tmp_data_path):
    for i in range(30):
        add_history_entry(tmp_data_path, _make_entry(uuid=f"e-{i}"), max_items=-1)
    assert len(load_history(tmp_data_path)) == 30

    trim_history(tmp_data_path, 10)
    loaded = load_history(tmp_data_path)
    assert len(loaded) == 10
    assert loaded[0].uuid == "e-20"


def test_trim_history_unlimited_noop(tmp_data_path):
    for i in range(15):
        add_history_entry(tmp_data_path, _make_entry(uuid=f"e-{i}"), max_items=-1)

    trim_history(tmp_data_path, -1)
    assert len(load_history(tmp_data_path)) == 15
