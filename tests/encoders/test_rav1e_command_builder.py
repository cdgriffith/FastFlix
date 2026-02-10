# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.rav1e.command_builder import build
from fastflix.models.encode import rav1eSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(hdr10=False, **kwargs):
    """Helper to build rav1e commands with custom settings."""
    defaults = dict(
        qp=80,
        speed="-1",
        tile_columns="-1",
        tile_rows="-1",
        tiles="0",
        single_pass=False,
        bitrate=None,
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=rav1eSettings(**defaults),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None),
        hdr10_metadata=hdr10,
    )
    with mock.patch("fastflix.encoders.rav1e.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])
        with mock.patch("fastflix.encoders.rav1e.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []
            result = build(fastflix)
    return result


def test_rav1e_basic_qp():
    """Test basic QP encoding with default settings."""
    result = _build_with_settings()
    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-qp" in cmd
    assert "80" in cmd
    assert "-speed" in cmd
    assert "-1" in cmd
    # Default tune is Psychovisual
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "tune=Psychovisual" in cmd[idx + 1]
    # -strict experimental should not be present
    assert "-strict" not in cmd


def test_rav1e_bitrate_single_pass():
    """Test bitrate mode with single pass."""
    result = _build_with_settings(qp=None, bitrate="3000k", single_pass=True)
    assert len(result) == 1
    cmd = result[0].command
    assert "-b:v" in cmd
    assert "3000k" in cmd
    assert "-pass" not in cmd


def test_rav1e_bitrate_two_pass():
    """Test bitrate mode with two pass."""
    result = _build_with_settings(qp=None, bitrate="3000k", single_pass=False)
    assert len(result) == 2
    cmd1 = result[0].command
    cmd2 = result[1].command
    assert "-b:v" in cmd1
    assert "3000k" in cmd1
    assert "-pass" in cmd1
    assert "1" in cmd1
    assert "-b:v" in cmd2
    assert "3000k" in cmd2
    assert "-pass" in cmd2
    assert "2" in cmd2


def test_rav1e_tune_psychovisual():
    """Test tune parameter is included when not default."""
    result = _build_with_settings(tune="Psychovisual")
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "tune=Psychovisual" in cmd[idx + 1]


def test_rav1e_tune_psnr():
    """Test tune Psnr parameter."""
    result = _build_with_settings(tune="Psnr")
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "tune=Psnr" in cmd[idx + 1]


def test_rav1e_tune_default_not_included():
    """Test that default tune is not added to params."""
    result = _build_with_settings(tune="default")
    cmd = result[0].command
    if "-rav1e-params" in cmd:
        idx = cmd.index("-rav1e-params")
        assert "tune=" not in cmd[idx + 1]


def test_rav1e_photon_noise():
    """Test photon noise parameter is included when > 0."""
    result = _build_with_settings(photon_noise=8)
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "photon_noise=8" in cmd[idx + 1]


def test_rav1e_photon_noise_zero_not_included():
    """Test photon noise is not added when 0."""
    result = _build_with_settings(photon_noise=0)
    cmd = result[0].command
    if "-rav1e-params" in cmd:
        idx = cmd.index("-rav1e-params")
        assert "photon_noise=" not in cmd[idx + 1]


def test_rav1e_scene_detection_disabled():
    """Test no_scene_detection is added when scene detection disabled."""
    result = _build_with_settings(scene_detection=False)
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "no_scene_detection=true" in cmd[idx + 1]


def test_rav1e_scene_detection_enabled():
    """Test no_scene_detection is not added when scene detection enabled."""
    result = _build_with_settings(scene_detection=True)
    cmd = result[0].command
    if "-rav1e-params" in cmd:
        idx = cmd.index("-rav1e-params")
        assert "no_scene_detection" not in cmd[idx + 1]


def test_rav1e_rav1e_params():
    """Test pass-through rav1e params."""
    result = _build_with_settings(rav1e_params=["low_latency=true", "threads=4"])
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    assert "low_latency=true" in cmd[idx + 1]
    assert "threads=4" in cmd[idx + 1]


def test_rav1e_no_rav1e_params_when_nothing_set():
    """Test -rav1e-params not added when nothing to set."""
    result = _build_with_settings(tune="default", photon_noise=0, scene_detection=True, rav1e_params=[])
    cmd = result[0].command
    assert "-rav1e-params" not in cmd


def test_rav1e_hdr10_metadata():
    """Test HDR10 metadata is passed via rav1e-params."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    params = cmd[idx + 1]
    assert "mastering_display=" in params
    assert "content_light=" in params


def test_rav1e_hdr10_not_included_when_8bit():
    """Test HDR10 metadata not added for 8-bit pixel format."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p")
    cmd = result[0].command
    if "-rav1e-params" in cmd:
        idx = cmd.index("-rav1e-params")
        params = cmd[idx + 1]
        assert "mastering_display=" not in params


def test_rav1e_all_elements_are_strings():
    """Test that all command elements are strings."""
    result = _build_with_settings()
    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"


def test_rav1e_combined_params():
    """Test multiple rav1e-params are combined correctly with colon separator."""
    result = _build_with_settings(
        tune="Psychovisual",
        photon_noise=16,
        scene_detection=False,
        rav1e_params=["threads=8"],
    )
    cmd = result[0].command
    assert "-rav1e-params" in cmd
    idx = cmd.index("-rav1e-params")
    params = cmd[idx + 1]
    parts = params.split(":")
    param_keys = [p.split("=")[0] for p in parts]
    assert "threads" in param_keys
    assert "tune" in param_keys
    assert "photon_noise" in param_keys
    assert "no_scene_detection" in param_keys
