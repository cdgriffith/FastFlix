# -*- coding: utf-8 -*-
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fastflix import gpu_detect
from fastflix.gpu_detect import DetectGPU, classify_vendor


@pytest.mark.parametrize(
    "name,expected",
    [
        ("NVIDIA", "NVIDIA"),
        ("NVIDIA Corporation", "NVIDIA"),
        ("Intel(R) Corporation", "INTEL"),
        ("Intel Corporation", "INTEL"),
        ("Advanced Micro Devices, Inc.", "AMD"),
        ("ATI Technologies Inc.", "AMD"),
        ("AMD", "AMD"),
        ("Microsoft Basic Display Adapter", None),
        ("", None),
        (None, None),
    ],
)
def test_classify_vendor(name, expected):
    assert classify_vendor(name) == expected


def test_windows_detect_handles_none_values(monkeypatch):
    adapters = [
        SimpleNamespace(AdapterCompatibility="Advanced Micro Devices, Inc.", VideoProcessor=None),
        SimpleNamespace(AdapterCompatibility=None, VideoProcessor="x"),
        SimpleNamespace(AdapterCompatibility="NVIDIA", VideoProcessor="GeForce"),
    ]
    fake_wmi = SimpleNamespace(WMI=lambda: SimpleNamespace(Win32_VideoController=lambda: adapters))
    monkeypatch.setitem(__import__("sys").modules, "wmi", fake_wmi)
    result = gpu_detect.windows_gpu_detect()
    assert result.AMD and result.NVIDIA and not result.INTEL
    assert result.fingerprint == "GeForce"


def _setup(monkeypatch, nvenc_result, seven_zip_result):
    config = SimpleNamespace(gpu_fingerprint=None, seven_zip=None, nvencc=None, vceencc=None, qsvencc=None)
    monkeypatch.setattr(gpu_detect, "gpu_detect", lambda: DetectGPU(NVIDIA=True, fingerprint="fp"))
    monkeypatch.setattr(gpu_detect, "find_seven_zip_windows", lambda: None)
    monkeypatch.setattr(gpu_detect, "download_7zip", lambda stop: seven_zip_result)
    monkeypatch.setattr(gpu_detect, "download_rigaya", lambda *a, **k: nvenc_result)
    return config


def test_failed_download_does_not_store_fingerprint(monkeypatch):
    config = _setup(monkeypatch, None, Path("7zr.exe"))
    gpu_detect.automatic_rigaya_download(config, None, MagicMock(), MagicMock())
    assert config.gpu_fingerprint is None


def test_cancelled_7zip_does_not_crash_or_store(monkeypatch):
    config = _setup(monkeypatch, Path("nvenc.exe"), None)
    gpu_detect.automatic_rigaya_download(config, None, MagicMock(), MagicMock())
    assert config.gpu_fingerprint is None
    assert config.nvencc is None


def test_successful_download_stores_fingerprint(monkeypatch):
    config = _setup(monkeypatch, Path("nvenc.exe"), Path("7zr.exe"))
    gpu_detect.automatic_rigaya_download(config, None, MagicMock(), MagicMock())
    assert config.gpu_fingerprint == "fp"
    assert config.nvencc == Path("nvenc.exe")
