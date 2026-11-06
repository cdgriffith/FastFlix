# -*- coding: utf-8 -*-
"""#777: a saved encoder path that no longer exists must not be kept."""

from unittest import mock

from fastflix.command_runner import BackgroundRunner
from fastflix.models.config import Config


def test_missing_rigaya_path_is_searched_again(tmp_path, monkeypatch):
    real_exe = tmp_path / "VCEEncC64.exe"
    real_exe.write_text("")
    config_file = tmp_path / "fastflix.yaml"
    config_file.write_text(
        "version: 6.3.2\n"
        f"ffmpeg: '{tmp_path / 'ffmpeg.exe'}'\n"
        f"ffprobe: '{tmp_path / 'ffprobe.exe'}'\n"
        f"vceencc: '{tmp_path / 'gone' / 'VCEEncC64.exe'}'\n"
        f"nvencc: '{tmp_path / 'gone' / 'NVEncC64.exe'}'\n",
        encoding="utf-8",
    )
    (tmp_path / "ffmpeg.exe").write_text("")
    (tmp_path / "ffprobe.exe").write_text("")
    monkeypatch.setenv("FF_CONFIG", str(config_file))

    def fake_where(name, portable_mode=False):
        return real_exe if name == "VCEEncC64" else None

    with (
        mock.patch("fastflix.models.config.where", side_effect=fake_where),
        mock.patch("fastflix.models.config.find_component_file", return_value=None),
    ):
        config = Config()
        config.load()

    assert config.vceencc == real_exe
    assert config.nvencc is None


def test_existing_rigaya_path_is_kept(tmp_path, monkeypatch):
    exe = tmp_path / "custom" / "QSVEncC64.exe"
    exe.parent.mkdir()
    exe.write_text("")
    config_file = tmp_path / "fastflix.yaml"
    (tmp_path / "ffmpeg.exe").write_text("")
    (tmp_path / "ffprobe.exe").write_text("")
    config_file.write_text(
        "version: 6.3.2\n"
        f"ffmpeg: '{tmp_path / 'ffmpeg.exe'}'\n"
        f"ffprobe: '{tmp_path / 'ffprobe.exe'}'\n"
        f"qsvencc: '{exe}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FF_CONFIG", str(config_file))
    with mock.patch("fastflix.models.config.where", return_value=None):
        config = Config()
        config.load()
    assert config.qsvencc == exe


def test_runner_reports_missing_program(tmp_path, caplog):
    runner = BackgroundRunner(log_queue=mock.MagicMock())
    missing = str(tmp_path / "nope" / "VCEEncC64.exe")
    with caplog.at_level("ERROR", logger="fastflix-core"):
        runner.start_exec([missing, "--version"], work_dir=str(tmp_path))
    assert runner.error_detected
    assert missing in caplog.text
    assert "does not exist" in caplog.text
