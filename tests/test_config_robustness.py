# -*- coding: utf-8 -*-
import logging
from pathlib import Path

import pytest
from box import Box

from fastflix.exceptions import ConfigError
from fastflix.models import config as config_module
from fastflix.models.config import Config


@pytest.fixture
def cfg_env(tmp_path, monkeypatch):
    fake_ff = tmp_path / "ffmpeg.exe"
    fake_ff.write_text("x")
    monkeypatch.setattr(config_module, "find_ffmpeg_file", lambda *a, **k: fake_ff)
    path = tmp_path / "cfg" / "fastflix.yaml"
    path.parent.mkdir()
    monkeypatch.setenv("FF_CONFIG", str(path))
    return path


def _new_config():
    c = Config()
    return c


def test_save_keeps_backup_of_previous_good_file(cfg_env):
    c = _new_config()
    c.config_path = cfg_env
    c.theme = "first"
    c.save()
    assert not cfg_env.with_name(cfg_env.name + ".bak").exists()
    c.theme = "second"
    c.save()
    bak = cfg_env.with_name(cfg_env.name + ".bak")
    assert Box.from_yaml(filename=bak).theme == "first"
    assert Box.from_yaml(filename=cfg_env).theme == "second"
    assert [p.name for p in cfg_env.parent.iterdir() if p.name.endswith(".tmp")] == []


def test_save_failure_leaves_original_intact(cfg_env, monkeypatch):
    c = _new_config()
    c.config_path = cfg_env
    c.theme = "good"
    c.save()

    def boom(self, *a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(Box, "to_yaml", boom)
    with pytest.raises(OSError):
        c.save()
    assert Box.from_yaml(filename=cfg_env).theme == "good"
    assert [p.name for p in cfg_env.parent.iterdir() if p.name.endswith(".tmp")] == []


def test_load_truncated_main_recovers_from_bak(cfg_env, caplog):
    c = _new_config()
    c.config_path = cfg_env
    c.theme = "keepme"
    c.save()
    c.theme = "latest"
    c.save()
    cfg_env.write_text("version: 6.\ntheme: [unclosed")
    loaded = Config()
    with caplog.at_level(logging.WARNING, logger="fastflix"):
        loaded.load()
    assert loaded.theme == "keepme"
    assert list(cfg_env.parent.glob("fastflix.yaml.corrupt-*"))


def test_load_corrupt_no_bak_moves_aside_and_uses_defaults(cfg_env):
    cfg_env.write_text("version: 6.\ntheme: [unclosed")
    loaded = Config()
    loaded.load()
    assert loaded.theme == Config().theme
    corrupt = list(cfg_env.parent.glob("fastflix.yaml.corrupt-*"))
    assert len(corrupt) == 1
    assert "unclosed" in corrupt[0].read_text()
    assert cfg_env.exists()


def test_load_tiny_file_with_bak_uses_bak(cfg_env):
    c = _new_config()
    c.config_path = cfg_env
    c.theme = "keepme"
    c.save()
    c.save()
    cfg_env.write_text("abc")
    loaded = Config()
    loaded.load()
    assert loaded.theme == "keepme"


def test_bad_profile_is_skipped(cfg_env):
    c = _new_config()
    c.config_path = cfg_env
    c.save()
    data = Box.from_yaml(filename=cfg_env)
    data.profiles = {"Broken": {"profile_version": 2, "x265": {"preset": {"nested": "bad"}}, "auto_crop": "zzz"}}
    data.theme = "mine"
    data.to_yaml(filename=cfg_env)
    loaded = Config()
    loaded.load()
    assert "Broken" not in loaded.profiles
    assert loaded.theme == "mine"


def test_wrongly_typed_top_level_values_ignored(cfg_env):
    c = _new_config()
    c.config_path = cfg_env
    c.save()
    data = Box.from_yaml(filename=cfg_env)
    data.logging_level = "abc"
    data.flat_ui = [1, 2]
    data.ui_scale = 2
    data.to_yaml(filename=cfg_env)
    loaded = Config()
    loaded.load()
    assert loaded.logging_level == Config().logging_level
    assert loaded.flat_ui is True
    assert loaded.ui_scale == "2"


def test_upgrade_check_sets_ffprobe(cfg_env, tmp_path):
    old = cfg_env.parent / "fastflix.json"
    old.write_text('{"ffmpeg": "/a/ffmpeg", "ffprobe": "/a/ffprobe"}')
    c = _new_config()
    c.config_path = cfg_env
    assert c.upgrade_check()
    assert c.ffmpeg == Path("/a/ffmpeg")
    assert c.ffprobe == Path("/a/ffprobe")


def test_pre_load_logs_exception(cfg_env, caplog):
    cfg_env.write_text("a: [unclosed")
    with caplog.at_level(logging.WARNING, logger="fastflix"):
        out = Config().pre_load()
    assert out == {"enable_scaling": True}
    assert any("config" in r.getMessage().lower() for r in caplog.records)


def test_unrecoverable_raises_config_error(cfg_env, monkeypatch):
    cfg_env.write_text("version: 6.\ntheme: [unclosed")

    def nope(*a, **k):
        raise OSError("locked")

    monkeypatch.setattr(config_module.os, "replace", nope)
    monkeypatch.setattr(config_module.shutil, "move", nope)
    with pytest.raises(ConfigError):
        Config().load()
