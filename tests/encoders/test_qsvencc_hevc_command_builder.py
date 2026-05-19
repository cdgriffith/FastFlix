# -*- coding: utf-8 -*-
from pathlib import Path
from unittest import mock

from box import Box

from fastflix.encoders.qsvencc_hevc.command_builder import build
from fastflix.models.encode import QSVEncCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _make_fastflix(encoder_settings, video_settings=None, stream_extras=None):
    """Create a FastFlix instance with QSVEncC-compatible video stream data."""
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
    fastflix.config.qsvencc = Path("QSVEncC64")
    return fastflix


def test_qsvencc_hevc_basic_cqp():
    """Test QSVEncC HEVC build with CQP mode produces all-string command list."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            preset="best",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--cqp" in cmd
    assert "22" in cmd
    assert "--quality" in cmd
    assert "best" in cmd
    assert "-c" in cmd
    assert "hevc" in cmd
    assert "QSVEncC64" in cmd


def test_qsvencc_hevc_tune_hq():
    """Test that --tune hq is added to the command when tune is set."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            tune="hq",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--tune" in cmd
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == "hq"


def test_qsvencc_hevc_tune_ll():
    """Test that --tune ll (low latency) is added to the command."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            tune="ll",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--tune" in cmd
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == "ll"


def test_qsvencc_hevc_tune_ull():
    """Test that --tune ull (ultra low latency) is added to the command."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            tune="ull",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--tune" in cmd
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == "ull"


def test_qsvencc_hevc_tune_lossless():
    """Test that --tune lossless is added to the command."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            tune="lossless",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--tune" in cmd
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == "lossless"


def test_qsvencc_hevc_tune_none():
    """Test that --tune is NOT in the command when tune is None."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate=None,
            cqp=22,
            tune=None,
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert "--tune" not in cmd


def test_qsvencc_hevc_tune_default_is_none():
    """Test that tune defaults to None when not specified."""
    settings = QSVEncCSettings(bitrate=None, cqp=22)
    assert settings.tune is None


def test_qsvencc_hevc_with_bitrate():
    """Test QSVEncC HEVC build with VBR bitrate mode."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate="6000k",
            cqp=None,
            preset="best",
        ),
    )

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "--vbr" in cmd
    assert "6000" in cmd
    assert "--cqp" not in cmd


def test_qsvencc_hevc_all_elements_are_strings():
    """Comprehensive test: build with many options and verify all elements are strings."""
    fastflix = _make_fastflix(
        encoder_settings=QSVEncCSettings(
            bitrate="5000k",
            cqp=None,
            preset="best",
            level="5.1",
            lookahead="32",
            b_frames="3",
            ref="4",
            tune="hq",
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

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "--tune" in cmd
    assert "--quality" in cmd
