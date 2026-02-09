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
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["--color_details"]

            result = build(fastflix)

            # The expected command should include the CRF setting and other basic parameters
            expected_command = [
                "ffmpeg",
                "-y",
                "-i",
                "input.mkv",
                "--color_details",
                "-crf:v",
                "23",
                "-preset:v",
                "medium",
                "output.mkv",
            ]
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
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["--color_details"]

            # Mock the secrets.token_hex function to return a predictable result
            with mock.patch("fastflix.encoders.avc_x264.command_builder.secrets.token_hex") as mock_token_hex:
                mock_token_hex.return_value = "abcdef1234"

                result = build(fastflix)

                # The expected command should be a list of two Command objects for two-pass encoding
                if reusables.win_based:
                    pass_log = "work_path\\pass_log_file_abcdef1234"
                else:
                    pass_log = "work_path/pass_log_file_abcdef1234"

                expected_command_1 = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    "input.mkv",
                    "--color_details",
                    "-pass",
                    "1",
                    "-passlogfile",
                    pass_log,
                    "-b:v",
                    "5000k",
                    "-preset:v",
                    "medium",
                    "-an",
                    "-sn",
                    "-dn",
                    "-r",
                    "24",
                    "-f",
                    "mp4",
                    "NUL" if reusables.win_based else "/dev/null",
                ]
                expected_command_2 = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    "input.mkv",
                    "--color_details",
                    "-pass",
                    "2",
                    "-passlogfile",
                    pass_log,
                    "-b:v",
                    "5000k",
                    "-preset:v",
                    "medium",
                    "output.mkv",
                ]
                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"
                assert result[0].command == expected_command_1, (
                    f"Expected: {expected_command_1}\nGot: {result[0].command}"
                )
                assert result[1].command == expected_command_2, (
                    f"Expected: {expected_command_2}\nGot: {result[1].command}"
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
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["--color_details"]

            result = build(fastflix)

            # The expected command should include the bitrate setting
            expected_command = [
                "ffmpeg",
                "-y",
                "-i",
                "input.mkv",
                "--color_details",
                "-b:v",
                "5000k",
                "-preset:v",
                "medium",
                "output.mkv",
            ]
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
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["--color_details"]

            result = build(fastflix)

            # The expected command should include the profile and tune settings
            expected_command = [
                "ffmpeg",
                "-y",
                "-i",
                "input.mkv",
                "-tune:v",
                "film",
                "--color_details",
                "-profile:v",
                "high",
                "-crf:v",
                "23",
                "-preset:v",
                "medium",
                "output.mkv",
            ]
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_avc_x264_aq_mode():
    """Test the build function with aq-mode setting."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate=None,
            aq_mode="autovariance",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            assert len(result) == 1
            cmd = result[0].command
            assert "-aq-mode" in cmd
            assert "2" in cmd


def test_avc_x264_psy_rd():
    """Test the build function with psy-rd setting."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate=None,
            psy_rd="1.0:0.15",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            assert len(result) == 1
            cmd = result[0].command
            assert "-psy-rd" in cmd
            assert "1.0:0.15" in cmd


def test_avc_x264_level():
    """Test the build function with level setting."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate=None,
            level="4.1",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            assert len(result) == 1
            cmd = result[0].command
            assert "-level" in cmd
            assert "4.1" in cmd


def test_avc_x264_x264_params():
    """Test the build function with custom x264 parameters."""
    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(
            crf=23,
            preset="medium",
            profile="default",
            tune=None,
            pix_fmt="yuv420p",
            bitrate=None,
            x264_params=["rc-lookahead=40", "ref=6"],
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            assert len(result) == 1
            cmd = result[0].command
            assert "-x264-params" in cmd
            params_idx = cmd.index("-x264-params")
            params_str = cmd[params_idx + 1]
            assert "rc-lookahead=40" in params_str
            assert "ref=6" in params_str


def test_avc_x264_defaults_no_extra():
    """Test that defaults don't add aq-mode/psy-rd/level/x264-params."""
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

    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch(
            "fastflix.encoders.avc_x264.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = []

            result = build(fastflix)

            assert len(result) == 1
            cmd = result[0].command
            assert "-aq-mode" not in cmd
            assert "-psy-rd" not in cmd
            assert "-level" not in cmd
            assert "-x264-params" not in cmd
