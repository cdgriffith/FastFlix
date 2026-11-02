# -*- coding: utf-8 -*-
import logging
import os
import time
from pathlib import Path

import pytest
from box import Box

from fastflix import ff_queue
from fastflix.ff_queue import get_queue, queue_file_lock, save_queue
from fastflix.models.encode import x265Settings
from fastflix.models.video import Video, VideoSettings


def _video(name):
    vs = VideoSettings(output_path=Path(f"/out/{name}.mkv"), video_encoder_settings=x265Settings())
    return Video(
        source=Path(f"/in/{name}.mkv"), work_path=Path(f"/work/{name}"), video_settings=vs, streams=Box(), format=Box()
    )


@pytest.fixture
def qfile(tmp_path):
    return tmp_path / "queue.yaml"


def _two_video_queue(qfile):
    save_queue([_video("a"), _video("b")], qfile)
    return qfile


def test_valid_queue_round_trip(qfile):
    _two_video_queue(qfile)
    out = get_queue(qfile)
    assert [v.source.name for v in out] == ["a.mkv", "b.mkv"]
    assert not list(qfile.parent.glob("queue_error_*"))


def test_bad_encoder_name_skips_only_that_item(qfile, caplog):
    _two_video_queue(qfile)
    data = Box.from_yaml(filename=qfile)
    data["queue"][0]["video_settings"]["video_encoder_settings"]["name"] = "Nonexistent Encoder"
    data.to_yaml(filename=qfile)
    with caplog.at_level(logging.WARNING, logger="fastflix"):
        out = get_queue(qfile)
    assert [v.source.name for v in out] == ["b.mkv"]
    assert len(list(qfile.parent.glob("queue_error_*.yaml"))) == 1


def test_missing_key_and_validation_error_skipped(qfile):
    save_queue([_video("a"), _video("b"), _video("c")], qfile)
    data = Box.from_yaml(filename=qfile)
    del data["queue"][0]["status"]
    data["queue"][1]["duration"] = "not a number"
    data.to_yaml(filename=qfile)
    out = get_queue(qfile)
    assert [v.source.name for v in out] == ["c.mkv"]
    assert len(list(qfile.parent.glob("queue_error_*.yaml"))) == 1


def test_save_uses_os_replace_and_leaves_no_tmp(qfile, monkeypatch):
    calls = []
    real = os.replace
    monkeypatch.setattr(ff_queue.os, "replace", lambda a, b: (calls.append((a, b)), real(a, b))[1])
    _two_video_queue(qfile)
    assert len(calls) == 1
    assert not list(qfile.parent.glob("queue_*.yaml.tmp"))


def test_get_queue_cleans_stale_tmp_files(qfile):
    _two_video_queue(qfile)
    stale = qfile.parent / "queue_abc123.yaml.tmp"
    stale.write_text("partial")
    old = time.time() - 3600
    os.utime(stale, (old, old))
    fresh = qfile.parent / "queue_fresh.yaml.tmp"
    fresh.write_text("in progress")
    get_queue(qfile)
    assert not stale.exists()
    assert fresh.exists()


def test_lock_records_pid_and_token(qfile):
    with queue_file_lock(qfile) as acquired:
        assert acquired
        content = qfile.with_suffix(".lock").read_text()
        assert content.startswith(f"{os.getpid()}:")
    assert not qfile.with_suffix(".lock").exists()


def test_stale_lock_removed_when_unchanged(qfile):
    lock = qfile.with_suffix(".lock")
    lock.write_text("999999:deadbeef")
    old = time.time() - 120
    os.utime(lock, (old, old))
    with queue_file_lock(qfile, timeout=3) as acquired:
        assert acquired


def test_lock_not_removed_if_replaced_while_stale(qfile, monkeypatch):
    lock = qfile.with_suffix(".lock")
    lock.write_text("1:old")
    old = time.time() - 120
    os.utime(lock, (old, old))
    real_read = Path.read_text

    def swap(self, *a, **k):
        result = real_read(self, *a, **k)
        if self == lock and result == "1:old":
            lock.write_text("2:new")
        return result

    monkeypatch.setattr(Path, "read_text", swap)
    with queue_file_lock(qfile, timeout=0.5) as acquired:
        assert not acquired
    assert lock.read_text() == "2:new"


def test_timeout_does_not_delete_foreign_lock(qfile):
    lock = qfile.with_suffix(".lock")
    lock.write_text("1:other")
    with queue_file_lock(qfile, timeout=0.3) as acquired:
        assert not acquired
    assert lock.read_text() == "1:other"


def test_generation_mismatch_logs_warning(qfile, caplog):
    _two_video_queue(qfile)
    with caplog.at_level(logging.WARNING, logger="fastflix"):
        save_queue([_video("z")], qfile, expected_generation="stale")
    assert [v.source.name for v in get_queue(qfile)] == ["a.mkv", "b.mkv"]
    assert any("dropped" in r.getMessage().lower() and "stale" in r.getMessage() for r in caplog.records)
