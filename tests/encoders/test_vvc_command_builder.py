# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.vvc.command_builder import build
from fastflix.models.encode import VVCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(hdr10=False, remove_hdr=False, **kwargs):
    """Helper to build VVC commands with custom settings."""
    defaults = dict(
        qp=22,
        bitrate=None,
        preset="medium",
        tier="main",
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=VVCSettings(**defaults),
        video_settings=VideoSettings(remove_hdr=remove_hdr, maxrate=None, bufsize=None),
        hdr10_metadata=hdr10,
    )
    with mock.patch("fastflix.encoders.vvc.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])
        result = build(fastflix)
    return result


def test_vvc_basic_qp():
    """Test basic QP encoding with default settings."""
    result = _build_with_settings()
    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-qp:v" in cmd
    assert "22" in cmd
    assert "-preset:v" in cmd
    assert "medium" in cmd


def test_vvc_bitrate_two_pass():
    """Test bitrate mode produces two-pass commands."""
    result = _build_with_settings(qp=None, bitrate="6000k")
    assert len(result) == 2
    cmd1 = result[0].command
    cmd2 = result[1].command
    assert "-b:v" in cmd1
    assert "6000k" in cmd1
    assert "-b:v" in cmd2
    assert "6000k" in cmd2


def test_vvc_tier():
    """Test tier parameter is included."""
    result = _build_with_settings(tier="high")
    cmd = result[0].command
    assert "-tier:v" in cmd
    idx = cmd.index("-tier:v")
    assert cmd[idx + 1] == "high"


def test_vvc_level():
    """Test level parameter is included when set."""
    result = _build_with_settings(levelidc="5.1")
    cmd = result[0].command
    assert "-level" in cmd
    idx = cmd.index("-level")
    assert cmd[idx + 1] == "5.1"


def test_vvc_subjopt_enabled_by_default():
    """Test that QPA is not disabled when subjopt is True (default)."""
    result = _build_with_settings(subjopt=True)
    cmd = result[0].command
    assert "-qpa" not in cmd


def test_vvc_subjopt_disabled():
    """Test that -qpa 0 is emitted when subjopt is False."""
    result = _build_with_settings(subjopt=False)
    cmd = result[0].command
    assert "-qpa" in cmd
    idx = cmd.index("-qpa")
    assert cmd[idx + 1] == "0"


def test_vvc_period():
    """Test intra period parameter is included when set."""
    result = _build_with_settings(period=2)
    cmd = result[0].command
    assert "-period" in cmd
    idx = cmd.index("-period")
    assert cmd[idx + 1] == "2"


def test_vvc_period_none():
    """Test period is not included when None."""
    result = _build_with_settings(period=None)
    cmd = result[0].command
    assert "-period" not in cmd


def test_vvc_threads():
    """Test threads parameter is included when > 0."""
    result = _build_with_settings(threads=8)
    cmd = result[0].command
    assert "-threads" in cmd
    idx = cmd.index("-threads")
    assert cmd[idx + 1] == "8"


def test_vvc_threads_auto():
    """Test threads is not included when 0 (auto)."""
    result = _build_with_settings(threads=0)
    cmd = result[0].command
    assert "-threads" not in cmd


def test_vvc_ifp_enabled():
    """Test IFP is appended to vvc-params when enabled."""
    result = _build_with_settings(ifp=True)
    cmd = result[0].command
    assert "-vvenc-params" in cmd
    idx = cmd.index("-vvenc-params")
    assert "ifp=1" in cmd[idx + 1]


def test_vvc_ifp_disabled():
    """Test IFP is not included when disabled."""
    result = _build_with_settings(ifp=False)
    cmd = result[0].command
    # Should not have vvenc-params at all with no other params
    if "-vvenc-params" in cmd:
        idx = cmd.index("-vvenc-params")
        assert "ifp=1" not in cmd[idx + 1]


def test_vvc_vvc_params():
    """Test pass-through vvc params."""
    result = _build_with_settings(vvc_params=["rcstatsfile=test"])
    cmd = result[0].command
    assert "-vvenc-params" in cmd
    idx = cmd.index("-vvenc-params")
    assert "rcstatsfile=test" in cmd[idx + 1]


def test_vvc_no_vvc_params_when_empty():
    """Test that -vvenc-params is not added when no params."""
    result = _build_with_settings(vvc_params=[], ifp=False)
    cmd = result[0].command
    assert "-vvenc-params" not in cmd


def test_vvc_all_elements_are_strings():
    """Test that all command elements are strings."""
    result = _build_with_settings()
    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"


def test_vvc_hdr10_mastering_display():
    """Test HDR10 mastering display metadata is passed to vvenc-params."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-vvenc-params" in cmd
    idx = cmd.index("-vvenc-params")
    params = cmd[idx + 1]
    assert "MasteringDisplayColourVolume=" in params


def test_vvc_hdr10_cll():
    """Test HDR10 content light level is passed to vvenc-params."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-vvenc-params" in cmd
    idx = cmd.index("-vvenc-params")
    params = cmd[idx + 1]
    assert "MaxContentLightLevel=1000,300" in params


def test_vvc_hdr10_color_primaries():
    """Test HDR10 color primaries are passed as FFmpeg flags."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-color_primaries" in cmd
    idx = cmd.index("-color_primaries")
    assert cmd[idx + 1] == "bt2020"


def test_vvc_hdr10_color_trc():
    """Test HDR10 color transfer is passed as FFmpeg flags."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-color_trc" in cmd
    idx = cmd.index("-color_trc")
    assert cmd[idx + 1] == "smpte2084"


def test_vvc_hdr10_colorspace():
    """Test HDR10 colorspace is passed as FFmpeg flags."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-colorspace" in cmd
    idx = cmd.index("-colorspace")
    assert cmd[idx + 1] == "bt2020nc"


def test_vvc_hdr10_not_included_when_remove_hdr():
    """Test HDR10 metadata is not included when remove_hdr is set."""
    result = _build_with_settings(hdr10=True, remove_hdr=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-color_primaries" not in cmd
    if "-vvenc-params" in cmd:
        idx = cmd.index("-vvenc-params")
        params = cmd[idx + 1]
        assert "MasteringDisplayColourVolume" not in params
        assert "MaxContentLightLevel" not in params


def test_vvc_hdr10_not_included_when_8bit():
    """Test HDR10 mastering display is not included for 8-bit output."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p")
    cmd = result[0].command
    # Color signaling should still be present (it's independent of bit depth)
    assert "-color_primaries" in cmd
    # But mastering display / CLL should not be in vvenc-params for 8-bit
    if "-vvenc-params" in cmd:
        idx = cmd.index("-vvenc-params")
        params = cmd[idx + 1]
        assert "MasteringDisplayColourVolume" not in params
        assert "MaxContentLightLevel" not in params


def test_vvc_hdr10_chroma_location():
    """Test chroma location is passed when present."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    assert "-chroma_sample_location" in cmd
    idx = cmd.index("-chroma_sample_location")
    assert cmd[idx + 1] == "0"  # "left" maps to 0


def test_vvc_hdr10_all_elements_are_strings():
    """Test that all command elements are strings with HDR10 metadata."""
    result = _build_with_settings(hdr10=True, pix_fmt="yuv420p10le")
    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
