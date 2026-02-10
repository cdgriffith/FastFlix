# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.av1_aom.command_builder import build
from fastflix.models.encode import AOMAV1Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(hdr10=False, **kwargs):
    """Helper to build AOM AV1 commands with custom settings."""
    defaults = dict(
        crf=26,
        cpu_used="4",
        usage="good",
        row_mt="enabled",
        tile_rows="0",
        tile_columns="0",
        bitrate=None,
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=AOMAV1Settings(**defaults),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None),
        hdr10_metadata=hdr10,
    )
    with mock.patch("fastflix.encoders.av1_aom.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])
        with mock.patch("fastflix.encoders.av1_aom.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []
            result = build(fastflix)
    return result


def test_aom_av1_basic_crf():
    """Test basic CRF encoding with default settings."""
    result = _build_with_settings()
    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-crf" in cmd
    assert "26" in cmd
    assert "-cpu-used" in cmd
    assert "4" in cmd
    assert "-usage" in cmd
    assert "good" in cmd
    assert "-row-mt" in cmd
    assert "1" in cmd
    # Default tune is ssim
    assert "-tune" in cmd
    tune_idx = cmd.index("-tune")
    assert cmd[tune_idx + 1] == "ssim"
    # -strict experimental should not be present
    assert "-strict" not in cmd


def test_aom_av1_bitrate_two_pass():
    """Test bitrate mode produces two-pass commands."""
    result = _build_with_settings(crf=None, bitrate="3000k")
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


def test_aom_av1_tune_psnr():
    """Test that tune parameter is included when not default."""
    result = _build_with_settings(tune="psnr")
    cmd = result[0].command
    assert "-tune" in cmd
    tune_idx = cmd.index("-tune")
    assert cmd[tune_idx + 1] == "psnr"


def test_aom_av1_tune_ssim():
    """Test tune ssim parameter."""
    result = _build_with_settings(tune="ssim")
    cmd = result[0].command
    assert "-tune" in cmd
    tune_idx = cmd.index("-tune")
    assert cmd[tune_idx + 1] == "ssim"


def test_aom_av1_tune_default_not_included():
    """Test that default tune is not added to command."""
    result = _build_with_settings(tune="default")
    cmd = result[0].command
    assert "-tune" not in cmd


def test_aom_av1_denoise():
    """Test that denoise parameter is included when > 0."""
    result = _build_with_settings(denoise_noise_level=10)
    cmd = result[0].command
    assert "-denoise-noise-level" in cmd
    idx = cmd.index("-denoise-noise-level")
    assert cmd[idx + 1] == "10"


def test_aom_av1_denoise_zero_not_included():
    """Test that denoise is not added when 0."""
    result = _build_with_settings(denoise_noise_level=0)
    cmd = result[0].command
    assert "-denoise-noise-level" not in cmd


def test_aom_av1_aq_mode():
    """Test that AQ mode is included when not default."""
    result = _build_with_settings(aq_mode="2")
    cmd = result[0].command
    assert "-aq-mode" in cmd
    idx = cmd.index("-aq-mode")
    assert cmd[idx + 1] == "2"


def test_aom_av1_aq_mode_default_not_included():
    """Test that default AQ mode is not added to command."""
    result = _build_with_settings(aq_mode="default")
    cmd = result[0].command
    assert "-aq-mode" not in cmd


def test_aom_av1_usage_allintra():
    """Test allintra usage mode."""
    result = _build_with_settings(usage="allintra")
    cmd = result[0].command
    assert "-usage" in cmd
    idx = cmd.index("-usage")
    assert cmd[idx + 1] == "allintra"


def test_aom_av1_aom_params():
    """Test pass-through aom params."""
    result = _build_with_settings(aom_params=["enable-cdef=0", "enable-restoration=0"])
    cmd = result[0].command
    assert "-aom-params" in cmd
    idx = cmd.index("-aom-params")
    assert "enable-cdef=0" in cmd[idx + 1]
    assert "enable-restoration=0" in cmd[idx + 1]


def test_aom_av1_no_aom_params_when_empty():
    """Test that -aom-params is not added when list is empty."""
    result = _build_with_settings(aom_params=[])
    cmd = result[0].command
    assert "-aom-params" not in cmd


def test_aom_av1_row_mt_disabled():
    """Test row-mt is not added when disabled."""
    result = _build_with_settings(row_mt="disabled")
    cmd = result[0].command
    assert "-row-mt" not in cmd


def test_aom_av1_all_elements_are_strings():
    """Test that all command elements are strings."""
    result = _build_with_settings()
    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
