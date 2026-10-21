# -*- coding: utf-8 -*-
import sys

from fastflix.resources import clean_env


def test_clean_env_unchanged_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/custom/lib")
    assert clean_env()["LD_LIBRARY_PATH"] == "/opt/custom/lib"


def test_clean_env_restores_original_in_pyinstaller(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/_MEI123", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/opt/custom/lib")
    env = clean_env()
    assert env["LD_LIBRARY_PATH"] == "/opt/custom/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in env


def test_clean_env_removes_bundled_path_in_pyinstaller(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/_MEI123", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    assert "LD_LIBRARY_PATH" not in clean_env()
