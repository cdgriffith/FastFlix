# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.vp9.command_builder import build
from fastflix.models.encode import VP9Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(**kwargs):
    """Helper to build VP9 commands with custom settings."""
    defaults = dict(
        crf=31,
        bitrate=None,
        quality="good",
        speed="0",
        row_mt=1,
        single_pass=False,
        profile=2,
        tile_columns="-1",
        tile_rows="-1",
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=VP9Settings(**defaults),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None),
    )
    with mock.patch("fastflix.encoders.vp9.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])
        with mock.patch("fastflix.encoders.vp9.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []
            result = build(fastflix)
    return result


def test_vp9_basic_crf():
    """Test basic CRF encoding with default settings."""
    result = _build_with_settings()
    assert len(result) == 2  # two-pass by default
    cmd = result[1].command
    assert isinstance(cmd, list)
    assert "-crf:v" in cmd
    assert "31" in cmd
    assert "-quality:v" in cmd
    assert "good" in cmd


def test_vp9_single_pass_crf():
    """Test single pass CRF mode."""
    result = _build_with_settings(single_pass=True)
    assert len(result) == 1
    cmd = result[0].command
    assert "-crf:v" in cmd


def test_vp9_bitrate_two_pass():
    """Test bitrate mode produces two-pass commands."""
    result = _build_with_settings(crf=None, bitrate="3000k")
    assert len(result) == 2
    cmd1 = result[0].command
    cmd2 = result[1].command
    assert "-b:v" in cmd1
    assert "3000k" in cmd1
    assert "-pass" in cmd1
    assert "-b:v" in cmd2
    assert "3000k" in cmd2


def test_vp9_auto_alt_ref():
    """Test auto-alt-ref parameter is included when >= 0."""
    result = _build_with_settings(auto_alt_ref=1)
    cmd = result[1].command
    assert "-auto-alt-ref" in cmd
    idx = cmd.index("-auto-alt-ref")
    assert cmd[idx + 1] == "1"


def test_vp9_auto_alt_ref_default_not_included():
    """Test auto-alt-ref is not included when -1 (default)."""
    result = _build_with_settings(auto_alt_ref=-1)
    cmd = result[1].command
    assert "-auto-alt-ref" not in cmd


def test_vp9_auto_alt_ref_disabled():
    """Test auto-alt-ref 0 (disabled) is emitted."""
    result = _build_with_settings(auto_alt_ref=0)
    cmd = result[1].command
    assert "-auto-alt-ref" in cmd
    idx = cmd.index("-auto-alt-ref")
    assert cmd[idx + 1] == "0"


def test_vp9_lag_in_frames():
    """Test lag-in-frames parameter is included when >= 0."""
    result = _build_with_settings(lag_in_frames=25)
    cmd = result[1].command
    assert "-lag-in-frames" in cmd
    idx = cmd.index("-lag-in-frames")
    assert cmd[idx + 1] == "25"


def test_vp9_lag_in_frames_default_not_included():
    """Test lag-in-frames is not included when -1 (default)."""
    result = _build_with_settings(lag_in_frames=-1)
    cmd = result[1].command
    assert "-lag-in-frames" not in cmd


def test_vp9_tune_content():
    """Test tune-content parameter is included when not default."""
    result = _build_with_settings(tune_content="screen")
    cmd = result[1].command
    assert "-tune-content" in cmd
    idx = cmd.index("-tune-content")
    assert cmd[idx + 1] == "screen"


def test_vp9_tune_content_film():
    """Test tune-content film."""
    result = _build_with_settings(tune_content="film")
    cmd = result[1].command
    assert "-tune-content" in cmd
    idx = cmd.index("-tune-content")
    assert cmd[idx + 1] == "film"


def test_vp9_tune_content_default_not_included():
    """Test tune-content is not included when default."""
    result = _build_with_settings(tune_content="default")
    cmd = result[1].command
    assert "-tune-content" not in cmd


def test_vp9_aq_mode():
    """Test aq-mode parameter is included when >= 0."""
    result = _build_with_settings(aq_mode=2)
    cmd = result[1].command
    assert "-aq-mode" in cmd
    idx = cmd.index("-aq-mode")
    assert cmd[idx + 1] == "2"


def test_vp9_aq_mode_default_not_included():
    """Test aq-mode is not included when -1 (default)."""
    result = _build_with_settings(aq_mode=-1)
    cmd = result[1].command
    assert "-aq-mode" not in cmd


def test_vp9_sharpness():
    """Test sharpness parameter is included when >= 0."""
    result = _build_with_settings(sharpness=4)
    cmd = result[1].command
    assert "-sharpness" in cmd
    idx = cmd.index("-sharpness")
    assert cmd[idx + 1] == "4"


def test_vp9_sharpness_default_not_included():
    """Test sharpness is not included when -1 (default)."""
    result = _build_with_settings(sharpness=-1)
    cmd = result[1].command
    assert "-sharpness" not in cmd


def test_vp9_all_new_options():
    """Test all new options together."""
    result = _build_with_settings(
        auto_alt_ref=6,
        lag_in_frames=25,
        tune_content="screen",
        aq_mode=3,
        sharpness=2,
    )
    cmd = result[1].command
    assert "-auto-alt-ref" in cmd
    assert "-lag-in-frames" in cmd
    assert "-tune-content" in cmd
    assert "-aq-mode" in cmd
    assert "-sharpness" in cmd


def test_vp9_all_elements_are_strings():
    """Test that all command elements are strings."""
    result = _build_with_settings()
    for r in result:
        cmd = r.command
        for i, element in enumerate(cmd):
            assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
