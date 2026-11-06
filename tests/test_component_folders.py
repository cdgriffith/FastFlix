# -*- coding: utf-8 -*-
import pytest

from fastflix import component_folders as cf
from fastflix.models import config as cfg


@pytest.fixture(autouse=True)
def reset_components_dir():
    cf.set_components_dir(None)
    yield
    cf.set_components_dir(None)


def test_default_is_appdata():
    assert cf.component_folder("FFmpeg") == cf.default_component_folder("FFmpeg")
    assert cf.component_search_folders("FFmpeg") == [cf.default_component_folder("FFmpeg")]


def test_custom_dir_used_for_downloads_with_appdata_fallback(tmp_path):
    cf.set_components_dir(tmp_path)
    assert cf.component_folder("NVEnc") == tmp_path / "NVEnc"
    assert cf.component_search_folders("NVEnc") == [tmp_path / "NVEnc", cf.default_component_folder("NVEnc")]


def test_find_component_file_prefers_custom_dir(tmp_path):
    cf.set_components_dir(tmp_path)
    (tmp_path / "NVEnc").mkdir()
    exe = tmp_path / "NVEnc" / "NVEncC64.exe"
    exe.write_bytes(b"x")
    assert cfg.find_component_file("NVEnc", "NVEncC64", "NVEncC") == exe


def test_find_ffmpeg_in_custom_bin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cfg.shutil, "which", lambda name: None)
    monkeypatch.delenv("FF_FFMPEG", raising=False)
    cf.set_components_dir(tmp_path / "comp")
    (tmp_path / "comp" / "FFmpeg" / "bin").mkdir(parents=True)
    exe = tmp_path / "comp" / "FFmpeg" / "bin" / "ffmpeg.exe"
    exe.write_bytes(b"x")
    assert cfg.find_ffmpeg_file("ffmpeg") == exe


def test_download_target_follows_setting(tmp_path):
    from fastflix import program_downloads as pd

    cf.set_components_dir(tmp_path)
    assert pd.component_folder("FFmpeg") == tmp_path / "FFmpeg"
