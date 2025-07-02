# -*- coding: utf-8 -*-
from unittest import mock

import reusables

from fastflix.encoders.avc_x264.command_builder import build
from fastflix.models.encode import x264Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_avc_x264_basic_crf():
    """Test the build function with basic CRF settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the CRF setting and other basic parameters
            expected_command = "ffmpeg -y -i input.mkv  --color_details  -crf:v 23 -preset:v medium   output.mkv"
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_avc_x264_two_pass_bitrate():
    """Test the build function with two-pass bitrate encoding."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=None,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate="5000k",
            bitrate_passes=2,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            # Mock the secrets.token_hex function to return a predictable result
            with mock.patch("fastflix.encoders.avc_x264.command_builder.secrets.token_hex") as mock_token_hex:
                mock_token_hex.return_value = "abcdef1234"

                result = build(fastflix)

                # The expected command should be a list of two Command objects for two-pass encoding
                if reusables.win_based:
                    expected_commands = [
                        'ffmpeg -y -i input.mkv  --color_details  -pass 1 -passlogfile "work_path\\pass_log_file_abcdef1234" -b:v 5000k -preset:v medium  -an -sn -dn -r 24 -f mp4 NUL',
                        'ffmpeg -y -i input.mkv  --color_details  -pass 2 -passlogfile "work_path\\pass_log_file_abcdef1234" -b:v 5000k -preset:v medium   output.mkv',
                    ]
                else:
                    expected_commands = [
                        'ffmpeg -y -i input.mkv  --color_details  -pass 1 -passlogfile "work_path/pass_log_file_abcdef1234" -b:v 5000k -preset:v medium  -an -sn -dn -r 24 -f mp4 /dev/null',
                        'ffmpeg -y -i input.mkv  --color_details  -pass 2 -passlogfile "work_path/pass_log_file_abcdef1234" -b:v 5000k -preset:v medium   output.mkv',
                    ]
                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"
                assert result[0].command == expected_commands[0], (
                    f"Expected: {expected_commands[0]}\nGot: {result[0].command}"
                )
                assert result[1].command == expected_commands[1], (
                    f"Expected: {expected_commands[1]}\nGot: {result[1].command}"
                )


def test_avc_x264_single_pass_bitrate():
    """Test the build function with single-pass bitrate encoding."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=None,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate="5000k",
            bitrate_passes=1,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the bitrate setting
            expected_command = "ffmpeg -y -i input.mkv  --color_details  -b:v 5000k -preset:v medium   output.mkv"
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_avc_x264_profile_tune():
    """Test the build function with profile and tune settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="high",
            tune="film",
            pix_fmt="yuv420p",
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the profile and tune settings
            expected_command = "ffmpeg -y -i input.mkv -tune:v film --color_details -profile:v high  -crf:v 23 -preset:v medium   output.mkv"
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"
