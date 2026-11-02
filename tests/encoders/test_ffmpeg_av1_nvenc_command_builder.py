# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.ffmpeg_av1_nvenc.command_builder import build
from fastflix.models.encode import FFmpegAV1NVENCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_ffmpeg_av1_nvenc_qp():
    """Test the build function with QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegAV1NVENCSettings(
            qp=28,
            preset="p5",
            tune="hq",
            pix_fmt="p010le",
            bitrate=None,
            spatial_aq=1,
            temporal_aq=1,
            rc_lookahead=16,
            tier="0",
            level=None,
            gpu=-1,
            b_ref_mode="middle",
            multipass="fullres",
            aq_strength=8,
            hw_accel=False,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        with mock.patch(
            "fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list)
            assert len(result) == 1

            cmd = result[0].command
            assert isinstance(cmd, list)

            assert "-tune:v" in cmd
            assert "hq" in cmd
            assert "-qp:v" in cmd
            assert "28" in cmd
            assert "-preset:v" in cmd
            assert "p5" in cmd
            assert "-spatial-aq:v" in cmd
            assert "1" in cmd
            assert "-temporal-aq:v" in cmd
            assert "-tier:v" in cmd
            assert "-rc-lookahead:v" in cmd
            assert "16" in cmd
            assert "-multipass:v" in cmd
            assert "fullres" in cmd
            assert "-b_ref_mode" in cmd
            assert "middle" in cmd
            assert "output.mkv" in cmd


def test_ffmpeg_av1_nvenc_bitrate():
    """Test the build function with bitrate encoding."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegAV1NVENCSettings(
            qp=None,
            preset="p5",
            tune="hq",
            pix_fmt="p010le",
            bitrate="5000k",
            spatial_aq=1,
            temporal_aq=1,
            rc_lookahead=16,
            tier="0",
            level=None,
            gpu=-1,
            b_ref_mode="middle",
            multipass="fullres",
            aq_strength=8,
            hw_accel=False,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        with mock.patch(
            "fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert "-b:v" in cmd
            assert "5000k" in cmd
            # FFmpeg NVENC does not support -pass/-2pass; two-pass is done internally via -multipass
            assert "-pass" not in cmd
            assert "-2pass" not in cmd
            assert "-multipass:v" in cmd
            assert "output.mkv" in cmd


def test_ffmpeg_av1_nvenc_with_rc_level():
    """Test the build function with RC and level settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegAV1NVENCSettings(
            qp=24,
            preset="p7",
            tune="uhq",
            pix_fmt="p010le",
            bitrate=None,
            spatial_aq=1,
            temporal_aq=1,
            rc_lookahead=20,
            tier="1",
            level="5.1",
            gpu=0,
            b_ref_mode="each",
            multipass="fullres",
            aq_strength=12,
            hw_accel=True,
            rc="vbr",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-hwaccel", "auto", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        with mock.patch(
            "fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list)
            assert len(result) == 1

            cmd = result[0].command
            assert isinstance(cmd, list)

            assert "-tune:v" in cmd
            assert "uhq" in cmd
            assert "-rc:v" in cmd
            assert "vbr" in cmd
            assert "-level:v" in cmd
            assert "5.1" in cmd
            assert "-spatial-aq:v" in cmd
            assert "-temporal-aq:v" in cmd
            assert "-tier:v" in cmd
            assert "1" in cmd
            assert "-rc-lookahead:v" in cmd
            assert "20" in cmd
            assert "-gpu" in cmd
            assert "0" in cmd
            assert "-b_ref_mode" in cmd
            assert "each" in cmd
            assert "-aq-strength:v" in cmd
            assert "12" in cmd
            assert "-multipass:v" in cmd
            assert "fullres" in cmd
            assert "-qp:v" in cmd
            assert "24" in cmd
            assert "output.mkv" in cmd


def test_ffmpeg_av1_nvenc_multipass_disabled():
    """Test that multipass flag is omitted when disabled."""
    fastflix = create_fastflix_instance(
        encoder_settings=FFmpegAV1NVENCSettings(
            qp=28,
            preset="p4",
            tune="hq",
            pix_fmt="yuv420p",
            bitrate=None,
            spatial_aq=0,
            temporal_aq=0,
            rc_lookahead=0,
            tier="0",
            level=None,
            gpu=-1,
            b_ref_mode="disabled",
            multipass="disabled",
            aq_strength=8,
            hw_accel=False,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        with mock.patch(
            "fastflix.encoders.ffmpeg_av1_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            cmd = result[0].command
            assert "-multipass:v" not in cmd
            assert "-aq-strength:v" not in cmd
