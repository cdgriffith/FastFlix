# -*- coding: utf-8 -*-
import logging
import os

from fastflix.models import history
from fastflix.models.history import (
    HistoryEntry,
    add_history_entry,
    delete_history_entry,
    get_history_file,
    get_history_thumbnails_dir,
    load_history,
    save_history,
    trim_history,
)


def _entry(uuid, thumb=""):
    return HistoryEntry(uuid=uuid, source="s", output="o", encoder_name="x265", thumbnail_filename=thumb)


def test_corrupt_history_not_overwritten_by_add(tmp_path, caplog):
    save_history(tmp_path, [_entry("1"), _entry("2")])
    hf = get_history_file(tmp_path)
    hf.write_text("entries: [unclosed")
    with caplog.at_level(logging.ERROR, logger="fastflix"):
        add_history_entry(tmp_path, _entry("3"))
    assert hf.read_text() == "entries: [unclosed"
    assert caplog.records


def test_corrupt_history_not_overwritten_by_trim_and_delete(tmp_path):
    hf = get_history_file(tmp_path)
    hf.write_text("entries: [unclosed")
    trim_history(tmp_path, 1)
    delete_history_entry(tmp_path, "1")
    assert hf.read_text() == "entries: [unclosed"


def test_missing_history_still_adds(tmp_path):
    add_history_entry(tmp_path, _entry("1"))
    assert [e.uuid for e in load_history(tmp_path)] == ["1"]


def test_load_history_returns_empty_on_corrupt(tmp_path):
    get_history_file(tmp_path).write_text("entries: [unclosed")
    assert load_history(tmp_path) == []


def test_save_history_is_atomic(tmp_path, monkeypatch):
    save_history(tmp_path, [_entry("1")])
    calls = []
    real = os.replace
    monkeypatch.setattr(history.os, "replace", lambda a, b: (calls.append(b), real(a, b))[1])
    save_history(tmp_path, [_entry("2")])
    assert calls
    assert [e.uuid for e in load_history(tmp_path)] == ["2"]
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_save_failure_keeps_old_file(tmp_path, monkeypatch):
    save_history(tmp_path, [_entry("1")])

    def boom(*a, **k):
        raise OSError("nope")

    monkeypatch.setattr(history.os, "replace", boom)
    save_history(tmp_path, [_entry("2")])
    monkeypatch.undo()
    assert [e.uuid for e in load_history(tmp_path)] == ["1"]
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_thumbnail_path_traversal_not_deleted(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    thumbs = get_history_thumbnails_dir(tmp_path)
    thumbs.mkdir()
    save_history(tmp_path, [_entry("1", "../victim.txt")])
    delete_history_entry(tmp_path, "1")
    assert victim.exists()


def test_thumbnail_normal_deleted(tmp_path):
    thumbs = get_history_thumbnails_dir(tmp_path)
    thumbs.mkdir()
    (thumbs / "a.jpg").write_text("x")
    save_history(tmp_path, [_entry("1", "a.jpg")])
    delete_history_entry(tmp_path, "1")
    assert not (thumbs / "a.jpg").exists()


def test_trim_nested_name_uses_basename_only(tmp_path):
    thumbs = get_history_thumbnails_dir(tmp_path)
    thumbs.mkdir()
    (thumbs / "a.jpg").write_text("x")
    save_history(tmp_path, [_entry("1", "sub/../../a.jpg"), _entry("2")])
    trim_history(tmp_path, 1)
    assert not (thumbs / "a.jpg").exists()
    assert [e.uuid for e in load_history(tmp_path)] == ["2"]
