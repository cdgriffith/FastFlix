# -*- coding: utf-8 -*-
from pathlib import Path
from unittest import mock

from box import Box

from fastflix.encoders.nvencc_hevc.command_builder import build
from fastflix.models.encode import NVEncCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _make_fastflix(encoder_settings, video_settings=None, stream_extras=None):
    """Create a FastFlix instance with NVEncC-compatible video stream data."""
    fastflix = create_fastflix_instance(encoder_settings=encoder_settings, video_settings=video_settings)
    # NVEncC command builders need stream fields that the base conftest doesn't set
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
    fastflix.config.nvencc = Path("NVEncC64")
    return fastflix


def test_nvencc_hevc_basic_cqp():
    """Test NVEncC HEVC build with CQP mode produces all-string command list."""
    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(
            bitrate=None,
            cqp=22,
            preset="quality",
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    # Every element must be a string (this was the bug - float values weren't wrapped)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--cqp" in cmd
    assert "22" in cmd
    assert "--preset" in cmd
    assert "quality" in cmd
    assert "-c" in cmd
    assert "hevc" in cmd
    assert "NVEncC64" in cmd


def test_nvencc_hevc_with_start_end_time():
    """Test that start_time and end_time (float values) are properly stringified."""
    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(bitrate=None, cqp=20),
        video_settings=VideoSettings(
            start_time=10.5,
            end_time=120.0,
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--seek" in cmd
    assert "10.5" in cmd
    assert "--seekto" in cmd
    assert "120.0" in cmd


def test_nvencc_hevc_with_source_fps():
    """Test that source_fps is properly stringified in the command."""
    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(bitrate=None, cqp=20),
        video_settings=VideoSettings(
            source_fps="24",
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--fps" in cmd
    assert "24" in cmd


def test_nvencc_hevc_with_bitrate():
    """Test NVEncC HEVC build with VBR bitrate mode."""
    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(
            bitrate="6000k",
            cqp=None,
            preset="quality",
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "--vbr" in cmd
    assert "6000" in cmd
    assert "--cqp" not in cmd


def test_nvencc_hevc_with_crop_scale():
    """Test NVEncC HEVC with crop and scale options."""
    from fastflix.models.video import Crop

    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(bitrate=None, cqp=20),
        video_settings=VideoSettings(
            crop=Crop(left=10, top=20, right=10, bottom=20, width=1900, height=1040),
            resolution_method="custom",
            resolution_custom="1280x720",
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--crop" in cmd
    assert "10,20,10,20" in cmd
    assert "--output-res" in cmd
    assert "1280x720" in cmd


def test_nvencc_hevc_all_elements_are_strings():
    """Comprehensive test: build with many options and verify all elements are strings.

    This is the key regression test for the float-to-string fix.
    """
    from fastflix.models.video import Crop

    fastflix = _make_fastflix(
        encoder_settings=NVEncCSettings(
            bitrate="5000k",
            cqp=None,
            preset="quality",
            tier="high",
            level="5.1",
            lookahead=32,
            aq="spatial",
            aq_strength=5,
            b_frames="3",
            ref="4",
            vbr_target="20",
        ),
        video_settings=VideoSettings(
            start_time=5.5,
            end_time=60.0,
            source_fps="30",
            remove_hdr=False,
            maxrate=8000,
            bufsize=16000,
            video_title="Test Title",
            crop=Crop(left=0, top=0, right=0, bottom=0, width=1920, height=1080),
        ),
    )

    with mock.patch("fastflix.encoders.nvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
