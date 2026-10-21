# -*- coding: utf-8 -*-
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from box import Box

from fastflix import flix
from fastflix.exceptions import FlixError


def test_concat_relative_entries_resolve_against_list_dir(tmp_path, monkeypatch):
    sub = tmp_path / "lists"
    sub.mkdir()
    (sub / "a.mkv").write_text("x")
    (sub / "b c.mkv").write_text("x")
    lst = sub / "list.txt"
    lst.write_text("# comment\nfile 'a.mkv'\nfile 'b c.mkv'\n")
    elsewhere = tmp_path / "other"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert flix.get_all_concat_items(lst) == [sub / "a.mkv", sub / "b c.mkv"]


def test_concat_handles_escaped_quote(tmp_path):
    (tmp_path / "it's.mkv").write_text("x")
    lst = tmp_path / "list.txt"
    lst.write_text("file 'it'\\''s.mkv'\n")
    assert flix.get_all_concat_items(lst) == [tmp_path / "it's.mkv"]


def test_concat_backslash_escape_unquoted(tmp_path):
    (tmp_path / "it's.mkv").write_text("x")
    lst = tmp_path / "list.txt"
    lst.write_text("file it\\'s.mkv\n")
    assert flix.get_all_concat_items(lst) == [tmp_path / "it's.mkv"]


def test_concat_absolute_and_missing(tmp_path):
    target = tmp_path / "abs.mkv"
    target.write_text("x")
    lst = tmp_path / "list.txt"
    lst.write_text(f"file '{target.as_posix()}'\n")
    assert flix.get_all_concat_items(lst) == [target]
    lst.write_text("file 'missing.mkv'\n")
    with pytest.raises(FlixError):
        flix.get_all_concat_items(lst)


def test_cropdetect_uses_frames_v(monkeypatch):
    captured = {}

    def fake_execute(cmd, **_):
        captured["cmd"] = cmd
        return SimpleNamespace(stderr="")

    monkeypatch.setattr(flix, "execute", fake_execute)
    flix.get_auto_crop(SimpleNamespace(ffmpeg="ffmpeg"), Path("a.mkv"), 1920, 1080, 0, 0, [])
    assert "-vframes" not in captured["cmd"]
    i = captured["cmd"].index("-frames:v")
    assert captured["cmd"][i + 1] == "10"


def test_extract_attachments_uses_basename_for_extension(monkeypatch):
    calls = []
    monkeypatch.setattr(flix, "extract_attachment", lambda *a: calls.append(a))
    app = MagicMock()
    app.fastflix.config.disable_cover_extraction = False
    app.fastflix.current_video.streams.attachment = [
        Box(index=3, tags={"filename": "some.dir/cover.jpg"}),
        Box(index=4, tags={"filename": "../cover.jpg"}),
        Box(index=5, tags={"filename": "other/notcover.jpg"}),
    ]
    flix.extract_attachments(app)
    assert [c[2] for c in calls] == [3, 4]
    assert all(c[4] == "cover.jpg" for c in calls)


def test_hdr10plus_ffprobe_selects_absolute_stream_index(monkeypatch):
    captured = {}

    def fake_execute(cmd, **_):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout='{"frames": []}')

    monkeypatch.setattr(flix, "execute", fake_execute)
    app = MagicMock()
    app.fastflix.current_video.source = Path("a.mkv")
    flix._detect_hdr10_plus_ffprobe(app, SimpleNamespace(ffprobe="ffprobe"), Box(index=2))
    i = captured["cmd"].index("-select_streams")
    assert captured["cmd"][i + 1] == "2"


class FakePopen:
    instances = []

    def __init__(self, cmd, **kw):
        self.cmd = cmd
        self.kw = kw
        self.stdout = MagicMock()
        self.stderr = MagicMock()
        self.stdin = MagicMock()
        self.killed = False
        self.waited = False
        FakePopen.instances.append(self)

    def communicate(self, *a, **k):
        if self.cmd[0] == "parser":
            return ("Dynamic HDR10+ metadata detected.", "")
        return ("", "")

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.waited = True
        return 0

    def poll(self):
        return None


def _tool_app():
    app = MagicMock()
    app.fastflix.current_video.source = Path("a.mkv")
    return app


def test_hdr10plus_tool_caps_frames_and_reaps_ffmpeg(monkeypatch):
    FakePopen.instances = []
    monkeypatch.setattr(flix, "Popen", FakePopen)
    monkeypatch.setattr(flix, "get_hdr10_parser_version", lambda c: flix.version.parse("1.0.0"))
    config = SimpleNamespace(ffmpeg="ffmpeg", hdr10plus_parser="parser")
    assert flix._detect_hdr10_plus_tool(_tool_app(), config, Box(index=0)) is True
    ffmpeg_proc, parser_proc = FakePopen.instances
    assert "-frames:v" in ffmpeg_proc.cmd
    assert ffmpeg_proc.killed and ffmpeg_proc.waited
    ffmpeg_proc.stdout.close.assert_called()


def test_hdr10plus_tool_reaps_ffmpeg_on_error(monkeypatch):
    FakePopen.instances = []

    class Boom(FakePopen):
        def communicate(self, *a, **k):
            if self.cmd[0] == "parser":
                raise RuntimeError("boom")
            return ("", "")

    monkeypatch.setattr(flix, "Popen", Boom)
    monkeypatch.setattr(flix, "get_hdr10_parser_version", lambda c: flix.version.parse("1.0.0"))
    config = SimpleNamespace(ffmpeg="ffmpeg", hdr10plus_parser="parser")
    assert flix._detect_hdr10_plus_tool(_tool_app(), config, Box(index=0)) is False
    assert FakePopen.instances[0].killed
