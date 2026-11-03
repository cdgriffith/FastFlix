# -*- coding: utf-8 -*-
import shutil
import subprocess

import pytest

from fastflix import shared
from fastflix.shared import quoted_path, select_release, safe_release_url

BS = "\\"


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/My Videos/a.mkv", "/My Videos/a.mkv"),
        ("a b.mkv", "a b.mkv"),
        ("C:/Videos/a.mkv", "C" + BS + ":/Videos/a.mkv"),
        ("C:" + BS + "Videos" + BS + "a.mkv", "C" + BS + ":" + BS * 2 + "Videos" + BS * 2 + "a.mkv"),
        ("it's.mkv", "it'" + BS * 3 + "''s.mkv"),
        ("  /x/a.mkv\n", "/x/a.mkv"),
        ("a\r\nb.mkv", "ab.mkv"),
        ("a\nb.mkv", "ab.mkv"),
    ],
)
def test_quoted_path(path, expected):
    assert quoted_path(path) == expected


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
@pytest.mark.parametrize("name", ["/My Videos/a: b.cube", "C:" + BS + "My Videos" + BS + "it's a.cube", "x'y''z.cube"])
def test_quoted_path_round_trips_through_ffmpeg(name):
    filt = f"lut3d=file='{quoted_path(name)}'"
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=0.1", "-vf", filt, "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    assert f"{name}: No such file or directory" in res.stderr


def rel(tag, prerelease=False, draft=False, assets=(), html="https://github.com/cdgriffith/FastFlix/releases/x"):
    return {"tag_name": tag, "prerelease": prerelease, "draft": draft, "assets": list(assets), "html_url": html}


def test_select_release_basic():
    data = [rel("6.2.1"), rel("6.3.0"), rel("6.1.0")]
    assert select_release(data)["tag_name"] == "6.3.0"


def test_select_release_tolerates_odd_tags():
    data = [rel("6.3.0-rc1"), rel("v6.3"), rel("nightly"), rel("6.2.1")]
    assert select_release(data)["tag_name"] == "v6.3"


def test_select_release_skips_prerelease_and_draft():
    data = [rel("7.0.0", prerelease=True), rel("7.1.0", draft=True), rel("6.2.1")]
    assert select_release(data)["tag_name"] == "6.2.1"


def test_select_release_empty():
    assert select_release([]) is None
    assert select_release([rel("junk")]) is None


def test_select_release_legacy_windows():
    data = [rel("6.0.0"), rel("4.9.1"), rel("4.10.0")]
    assert select_release(data, legacy_windows=True)["tag_name"] == "4.10.0"
    assert select_release([rel("6.0.0")], legacy_windows=True) is None


def test_safe_release_url():
    assert safe_release_url("https://github.com/cdgriffith/FastFlix/releases/download/6.3.0/a.zip")
    assert not safe_release_url("https://evil.example/cdgriffith/FastFlix/a.zip")
    assert not safe_release_url("http://github.com/cdgriffith/FastFlix/a.zip")
    assert not safe_release_url("https://github.com/cdgriffith/FastFlix.evil/a.zip")
    assert not safe_release_url(None)


def test_latest_fastflix_timeouts_and_bad_data(monkeypatch):
    calls = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_get(url, timeout):
        calls["timeout"] = timeout
        return Resp()

    monkeypatch.setattr(shared.requests, "get", fake_get)
    monkeypatch.setattr(shared, "message", lambda *a, **k: calls.setdefault("msg", True))
    shared.latest_fastflix(app=None, show_new_dialog=False)
    auto_timeout = calls["timeout"]
    shared.latest_fastflix(app=None, show_new_dialog=True)
    assert auto_timeout < calls["timeout"]


# --- #773 millisecond precision for Start/End time ---


@pytest.mark.parametrize(
    "text,expected",
    [
        ("01:05:45.003", 3945.003),
        ("03:05:45.009", 11145.009),
        ("02:02:56.077", 7376.077),
        ("02:02:56.07", 7376.07),
        ("02:02:56.0077", 7376.0077),
        ("0:00:01.05", 1.05),
        ("0:00:01.5", 1.5),
        ("0:00:01.500", 1.5),
        ("1:00:00", 3600),
        ("90.25", 90.25),
        ("0:00:10.", 10),
        ("0:00:01.abc", 0),
    ],
)
def test_time_to_number_keeps_leading_zero_fractions(text, expected):
    assert shared.time_to_number(text) == expected


@pytest.mark.parametrize(
    "number,expected",
    [
        (0, "0:00:00"),
        (3945.003, "1:05:45.003"),
        (11145.009, "3:05:45.009"),
        (1.5, "0:00:01.500"),
        (36000.25, "10:00:00.250"),
        (3946.0029999999, "1:05:46.003"),
    ],
)
def test_number_to_time_millisecond_precision(number, expected):
    assert shared.number_to_time(number) == expected


@pytest.mark.parametrize("seconds", [0, 0.001, 1.05, 3945.003, 11145.009, 36000.999])
def test_time_round_trip(seconds):
    assert shared.time_to_number(shared.number_to_time(seconds)) == seconds


def test_play_completion_sound_never_raises(monkeypatch):
    """#745 #755: a missing/broken sound backend must not break queue completion."""
    monkeypatch.setattr(shared.QtWidgets.QApplication, "beep", lambda: (_ for _ in ()).throw(RuntimeError("no audio")))
    monkeypatch.setattr(shared.sys, "platform", "linux")
    shared.play_completion_sound()
