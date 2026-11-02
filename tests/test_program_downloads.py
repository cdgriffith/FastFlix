# -*- coding: utf-8 -*-
import hashlib
from unittest.mock import MagicMock

import pytest

from fastflix import program_downloads as pd
from fastflix.exceptions import FastFlixError


def asset(name, **extra):
    return {"name": name, "browser_download_url": f"https://example.invalid/{name}", "size": 5000, **extra}


def test_stable_picks_non_shared_numeric_latest():
    assets = [
        asset("ffmpeg-n8.9-latest-win64-gpl-8.9.zip"),
        asset("ffmpeg-n8.10-latest-win64-gpl-8.10.zip"),
        asset("ffmpeg-n8.10-latest-win64-gpl-shared-8.10.zip"),
        asset("ffmpeg-n7.1-latest-win64-gpl-7.1.zip"),
    ]
    assert pd.select_stable_ffmpeg_asset(assets)["name"] == "ffmpeg-n8.10-latest-win64-gpl-8.10.zip"


def test_stable_ignores_shared_only():
    assert pd.select_stable_ffmpeg_asset([asset("ffmpeg-n8.0-latest-win64-gpl-shared-8.0.zip")]) is None


def test_stable_empty():
    assert pd.select_stable_ffmpeg_asset([]) is None


def test_latest_picks_exact_static_build():
    assets = [asset("ffmpeg-master-latest-win64-gpl-shared.zip"), asset("ffmpeg-master-latest-win64-gpl.zip")]
    assert pd.select_latest_ffmpeg_asset(assets)["name"] == "ffmpeg-master-latest-win64-gpl.zip"


def test_release_assets_rate_limit():
    with pytest.raises(FastFlixError, match="rate limit"):
        pd.release_assets({"message": "API rate limit exceeded for 1.2.3.4", "documentation_url": "x"})


def test_release_assets_ok():
    assert pd.release_assets({"assets": [1]}) == [1]


def test_get_release_json_uses_timeout_and_raises(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = {"assets": []}
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(pd.requests, "get", get)
    pd.get_release_json("https://api.github.com/x")
    assert get.call_args.kwargs["timeout"]
    resp.raise_for_status.assert_called_once()


def test_expected_sha_from_digest_field():
    a = asset("a.zip", digest="sha256:" + "ab" * 32)
    assert pd.expected_sha256(a, [a]) == "ab" * 32


def test_expected_sha_from_checksums_file(monkeypatch):
    a = asset("a.zip")
    sums = asset("checksums.sha256")
    resp = MagicMock()
    resp.text = f"{'cd' * 32} *a.zip\n{'ef' * 32}  b.zip\n"
    monkeypatch.setattr(pd.requests, "get", MagicMock(return_value=resp))
    assert pd.expected_sha256(a, [a, sums]) == "cd" * 32


def test_expected_sha_missing(monkeypatch):
    a = asset("a.zip")
    assert pd.expected_sha256(a, [a]) is None


def test_verify_sha256(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    good = hashlib.sha256(b"hello").hexdigest()
    pd.verify_sha256(f, good.upper())
    with pytest.raises(FastFlixError, match="checksum"):
        pd.verify_sha256(f, "00" * 32)
    pd.verify_sha256(f, None)  # warns, continues


def test_download_file_cancel(tmp_path, monkeypatch):
    resp = MagicMock()
    resp.iter_content.return_value = [b"a" * 1024] * 3
    monkeypatch.setattr(pd.requests, "get", MagicMock(return_value=resp))
    dest = tmp_path / "f.bin"
    assert pd.download_file("https://x", dest, lambda i: None, lambda: True) is False
    assert not dest.exists()


def test_download_file_ok(tmp_path, monkeypatch):
    resp = MagicMock()
    resp.iter_content.return_value = [b"a" * 1024] * 3
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(pd.requests, "get", get)
    dest = tmp_path / "f.bin"
    assert pd.download_file("https://x", dest, lambda i: None, lambda: False) is True
    assert dest.stat().st_size == 3072
    assert get.call_args.kwargs["timeout"]
    resp.raise_for_status.assert_called_once()
