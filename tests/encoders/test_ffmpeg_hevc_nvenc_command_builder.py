# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.ffmpeg_hevc_nvenc.command_builder import build
from fastflix.models.encode import FFmpegNVENCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_ffmpeg_hevc_nvenc_qp():
    """Test the build function with QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegNVENCSettings(
            qp=28,
            preset="slow",
            profile="main",
            tune="hq",
            pix_fmt="p010le",
            bitrate=None,
            spatial_aq=0,
            rc_lookahead=0,
            tier="main",
            level=None,
            gpu=-1,
            b_ref_mode="disabled",
            hw_accel=False,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert isinstance(cmd, list), f"Expected command to be a list, got {type(cmd)}"

            # Check key elements
            assert "-tune:v" in cmd
            assert "hq" in cmd
            assert "-qp:v" in cmd
            assert "28" in cmd
            assert "-preset:v" in cmd
            assert "slow" in cmd
            assert "-spatial-aq:v" in cmd
            assert "-tier:v" in cmd
            assert "main" in cmd
            assert "-profile:v" in cmd
            assert "output.mkv" in cmd


def test_ffmpeg_hevc_nvenc_bitrate():
    """Test the build function with bitrate encoding."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegNVENCSettings(
            qp=None,
            preset="slow",
            profile="main",
            tune="hq",
            pix_fmt="p010le",
            bitrate="6000k",
            spatial_aq=0,
            rc_lookahead=0,
            tier="main",
            level=None,
            gpu=-1,
            b_ref_mode="disabled",
            hw_accel=False,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert "-b:v" in cmd
            assert "6000k" in cmd
            # FFmpeg NVENC does not support -pass/-2pass; two-pass is done internally via -multipass
            assert "-pass" not in cmd
            assert "-2pass" not in cmd
            assert "-multipass:v" in cmd
            assert "output.mkv" in cmd


def test_ffmpeg_hevc_nvenc_with_rc_level():
    """Test the build function with RC and level settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegNVENCSettings(
            qp=28,
            preset="slow",
            profile="main",
            tune="hq",
            pix_fmt="p010le",
            bitrate=None,
            spatial_aq=1,
            rc_lookahead=32,
            tier="high",
            level="5.1",
            gpu=0,
            b_ref_mode="each",
            hw_accel=True,
            rc="vbr",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-hwaccel", "auto", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert isinstance(cmd, list), f"Expected command to be a list, got {type(cmd)}"

            # Check key elements
            assert "-tune:v" in cmd
            assert "hq" in cmd
            assert "-rc:v" in cmd
            assert "vbr" in cmd
            assert "-level:v" in cmd
            assert "5.1" in cmd
            assert "-spatial-aq:v" in cmd
            assert "1" in cmd
            assert "-tier:v" in cmd
            assert "high" in cmd
            assert "-rc-lookahead:v" in cmd
            assert "32" in cmd
            assert "-gpu" in cmd
            assert "0" in cmd
            assert "-b_ref_mode" in cmd
            assert "each" in cmd
            assert "-qp:v" in cmd
            assert "28" in cmd
            assert "output.mkv" in cmd
