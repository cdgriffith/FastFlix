# -*- coding: utf-8 -*-
from pathlib import Path
from unittest import mock

from box import Box

from fastflix.encoders.vceencc_hevc.command_builder import build
from fastflix.models.encode import VCEEncCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _make_fastflix(encoder_settings, video_settings=None, stream_extras=None):
    """Create a FastFlix instance with VCEEncC-compatible video stream data."""
    fastflix = create_fastflix_instance(encoder_settings=encoder_settings, video_settings=video_settings)
    stream_data = {
        "index": 0,
        "id": "0x1",
        "codec_name": "hevc",
        "codec_type": "video",
        "pix_fmt": "yuv420p10le",
        "color_space": "bt2020nc",
        "color_transfer": "smpte2084",
        "color_primaries": "bt2020",
        "chroma_location": "left",
        "bit_depth": 10,
        "r_frame_rate": "24000/1001",
        "avg_frame_rate": "24000/1001",
        "width": 1920,
        "height": 1080,
    }
    if stream_extras:
        stream_data.update(stream_extras)
    fastflix.current_video.streams = Box({"video": [Box(stream_data)], "audio": [], "subtitle": []})
    fastflix.config.vceencc = Path("VCEEncC64")
    return fastflix


def test_vceencc_hevc_basic_cqp():
    """Test VCEEncC HEVC build with CQP mode produces all-string command list."""
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(
            bitrate=None,
            cqp=22,
            preset="slow",
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--cqp" in cmd
    assert "22" in cmd
    assert "--preset" in cmd
    assert "slow" in cmd
    assert "-c" in cmd
    assert "hevc" in cmd


def test_vceencc_hevc_with_start_end_time():
    """Test that start_time and end_time (float values) are properly stringified.

    This is the key regression test: VCEEncC HEVC previously crashed with
    pydantic ValidationError because float values weren't converted to strings.
    """
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(bitrate=None, cqp=20),
        video_settings=VideoSettings(
            start_time=10.5,
            end_time=120.0,
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--seek" in cmd
    assert "10.5" in cmd
    assert "--seekto" in cmd
    assert "120.0" in cmd


def test_vceencc_hevc_with_source_fps():
    """Test that source_fps is properly stringified in the command."""
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(bitrate=None, cqp=20),
        video_settings=VideoSettings(
            source_fps="30",
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--fps" in cmd
    assert "30" in cmd


def test_vceencc_hevc_with_bitrate():
    """Test VCEEncC HEVC build with VBR bitrate mode."""
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(
            bitrate="6000k",
            cqp=None,
            preset="slow",
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "--vbr" in cmd
    assert "6000" in cmd
    assert "--cqp" not in cmd


def test_vceencc_hevc_cqp_float_coercion():
    """Test that CQP as float (e.g., from Qt spinbox) is handled properly.

    This was the original bug: the Qt widget returned 1.0 (float) which
    ended up in the command list without str() conversion.
    """
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(
            bitrate=None,
            cqp=1.0,  # Float, as it comes from Qt widget
            preset="slow",
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--cqp" in cmd


def test_vceencc_hevc_all_elements_are_strings():
    """Comprehensive test: build with many options and verify all elements are strings."""
    fastflix = _make_fastflix(
        encoder_settings=VCEEncCSettings(
            bitrate="5000k",
            cqp=None,
            preset="slow",
            tier="high",
            level="5.1",
            ref="4",
            min_q="10",
            max_q="51",
            vbaq=True,
            pre_encode=True,
        ),
        video_settings=VideoSettings(
            start_time=5.5,
            end_time=60.0,
            source_fps="24",
            remove_hdr=False,
            maxrate=8000,
            bufsize=16000,
            video_title="Test Title",
        ),
    )

    with mock.patch("fastflix.encoders.vceencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
