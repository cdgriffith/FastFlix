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

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the QP setting and other basic parameters
            expected_command = "ffmpeg -y -i input.mkv -tune:v hq --color_details -spatial_aq:v 0 -tier:v main -rc-lookahead:v 0 -gpu -1 -b_ref_mode disabled -profile:v main  -qp:v 28 -preset:v slow  output.mkv"
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


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

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            # Mock the secrets.token_hex function to return a predictable result
            with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.secrets.token_hex") as mock_token_hex:
                mock_token_hex.return_value = "abcdef1234"

                result = build(fastflix)

                # The expected command should be a list of two Command objects for two-pass encoding
                expected_commands = [
                    'ffmpeg -y -i input.mkv -tune:v hq --color_details -spatial_aq:v 0 -tier:v main -rc-lookahead:v 0 -gpu -1 -b_ref_mode disabled -profile:v main  -pass 1 -passlogfile "work_path\\pass_log_file_abcdef1234" -b:v 6000k -preset:v slow -2pass 1  -an -sn -dn -r 24 -f mp4 NUL',
                    'ffmpeg -y -i input.mkv -tune:v hq --color_details -spatial_aq:v 0 -tier:v main -rc-lookahead:v 0 -gpu -1 -b_ref_mode disabled -profile:v main  -pass 2 -passlogfile "work_path\\pass_log_file_abcdef1234" -2pass 1 -b:v 6000k -preset:v slow   output.mkv',
                ]
                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"
                assert result[0].command == expected_commands[0], (
                    f"Expected: {expected_commands[0]}\nGot: {result[0].command}"
                )
                assert result[1].command == expected_commands[1], (
                    f"Expected: {expected_commands[1]}\nGot: {result[1].command}"
                )


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

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -hwaccel auto -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.ffmpeg_hevc_nvenc.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the RC and level settings
            expected_command = "ffmpeg -hwaccel auto -y -i input.mkv -tune:v hq --color_details -spatial_aq:v 1 -tier:v high -rc-lookahead:v 32 -gpu 0 -b_ref_mode each -profile:v main -rc:v vbr -level:v 5.1  -qp:v 28 -preset:v slow  output.mkv"
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"
