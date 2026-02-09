# -*- coding: utf-8 -*-
from pathlib import Path

from fastflix.encoders.gifski.command_builder import build
from fastflix.models.encode import GifskiSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_gifski_basic_build():
    """Test basic gifski command generation with pipe approach."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="15",
            quality="90",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)

    assert isinstance(result, list)
    assert len(result) == 1

    cmd = result[0]
    assert cmd.shell is True
    assert cmd.exe == "gifski"
    assert isinstance(cmd.command, str)
    assert "yuv4mpegpipe" in cmd.command
    assert "--fps" in cmd.command
    assert "--quality" in cmd.command
    assert "|" in cmd.command
    assert "output.gif" in cmd.command


def test_gifski_with_lossy_quality():
    """Test gifski with lossy quality setting."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="10",
            quality="80",
            lossy_quality="60",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)
    cmd_str = result[0].command
    assert "--lossy-quality" in cmd_str


def test_gifski_with_motion_quality():
    """Test gifski with motion quality setting."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="15",
            quality="90",
            motion_quality="70",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)
    cmd_str = result[0].command
    assert "--motion-quality" in cmd_str


def test_gifski_fast_mode():
    """Test gifski with fast mode enabled."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="15",
            quality="90",
            fast=True,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)
    cmd_str = result[0].command
    assert "--fast" in cmd_str


def test_gifski_auto_qualities_excluded():
    """Test that 'auto' quality values are not passed as flags."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="15",
            quality="90",
            lossy_quality="auto",
            motion_quality="auto",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)
    cmd_str = result[0].command
    assert "--lossy-quality" not in cmd_str
    assert "--motion-quality" not in cmd_str


def test_gifski_with_start_end_time():
    """Test gifski with start and end time."""
    fastflix = create_fastflix_instance(
        encoder_settings=GifskiSettings(
            fps="15",
            quality="90",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
            start_time=5.0,
            end_time=15.0,
        ),
    )
    fastflix.config.gifski = Path("gifski")

    result = build(fastflix)
    cmd_str = result[0].command
    assert "-ss" in cmd_str
    assert "-to" in cmd_str
