# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.svt_av1_avif.command_builder import build
from fastflix.models.encode import SVTAVIFSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(**kwargs):
    """Helper to build AVIF commands with custom settings."""
    defaults = dict(
        qp=24,
        qp_mode="qp",
        speed="7",
        single_pass=True,
        bitrate=None,
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAVIFSettings(**defaults),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None),
    )
    with mock.patch("fastflix.encoders.svt_av1_avif.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.avif"], ["-r", "24"])
        with mock.patch("fastflix.encoders.svt_av1_avif.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []
            result = build(fastflix)
    return result


def test_svt_av1_avif_basic():
    """Test basic AVIF encoding with default settings."""
    result = _build_with_settings()
    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-f" in cmd
    assert "avif" in cmd
    assert "-qp" in cmd
    assert "24" in cmd
    assert "-strict" in cmd
    assert "experimental" in cmd


def test_svt_av1_avif_with_tune():
    """Test that tune parameter is included when non-default."""
    result = _build_with_settings(tune="2")
    cmd = result[0].command
    params_idx = cmd.index("-svtav1-params")
    params_value = cmd[params_idx + 1]
    assert "tune=2" in params_value


def test_svt_av1_avif_with_sharpness():
    """Test that sharpness parameter is included when non-default."""
    result = _build_with_settings(sharpness="-3")
    cmd = result[0].command
    params_idx = cmd.index("-svtav1-params")
    params_value = cmd[params_idx + 1]
    assert "sharpness=-3" in params_value


def test_svt_av1_avif_defaults_no_extra_params():
    """Test that default settings don't add tune or sharpness to svtav1-params."""
    result = _build_with_settings()
    cmd = result[0].command
    # With defaults, there should be no svtav1-params at all (no custom params set)
    if "-svtav1-params" in cmd:
        params_idx = cmd.index("-svtav1-params")
        params_value = cmd[params_idx + 1]
        assert "tune=" not in params_value
        assert "sharpness=" not in params_value


def test_svt_av1_avif_bitrate():
    """Test AVIF encoding with bitrate mode."""
    result = _build_with_settings(qp=None, bitrate="2000k")
    assert len(result) == 1
    cmd = result[0].command
    assert "-b:v" in cmd
    assert "2000k" in cmd
    assert "-f" in cmd
    assert "avif" in cmd
