# -*- coding: utf-8 -*-
from unittest import mock

import reusables

from fastflix.encoders.hevc_x265.command_builder import build
from fastflix.models.encode import x265Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_hevc_x265_basic_crf():
    """Test the build function with basic CRF settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=x265Settings(
            crf=22,
            preset="medium",
            profile="default",
            tune="default",
            hdr10=False,
            hdr10_opt=False,
            repeat_headers=False,
            aq_mode=2,
            bframes=4,
            b_adapt=2,
            frame_threads=0,
            intra_smoothing=True,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", None)

        result = build(fastflix)

        # The expected command should include the CRF setting and other basic parameters
        expected_command = 'ffmpeg -y -i input.mkv  -x265-params "aq-mode=2:repeat-headers=0:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=0:hdr10=0:chromaloc=0"   -crf:v 22 -preset:v medium   output.mkv'
        assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
        assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
        assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_hevc_x265_two_pass_bitrate():
    """Test the build function with two-pass bitrate encoding."""
    fastflix = create_fastflix_instance(
        encoder_settings=x265Settings(
            crf=None,
            preset="medium",
            profile="default",
            tune="default",
            hdr10=False,
            hdr10_opt=False,
            repeat_headers=False,
            aq_mode=2,
            bframes=4,
            b_adapt=2,
            frame_threads=0,
            intra_smoothing=True,
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
    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", None)
        # Mock the secrets.token_hex function to return a predictable result
        with mock.patch("fastflix.encoders.hevc_x265.command_builder.secrets.token_hex") as mock_token_hex:
            mock_token_hex.return_value = "abcdef1234"

            result = build(fastflix)

            # The expected command should be a list of two Command objects for two-pass encoding
            expected_commands = [
                f'ffmpeg -y -i input.mkv  -x265-params "aq-mode=2:repeat-headers=0:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=0:hdr10=0:chromaloc=0:pass=1:no-slow-firstpass=1:stats=pass_log_file_abcdef1234.log"   -b:v 5000k -preset:v medium   -an -sn -dn None -f mp4 {"NUL" if reusables.win_based else "/dev/null"}',
                'ffmpeg -y -i input.mkv  -x265-params "aq-mode=2:repeat-headers=0:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=0:hdr10=0:chromaloc=0:pass=2:stats=pass_log_file_abcdef1234.log"   -b:v 5000k -preset:v medium   output.mkv',
            ]
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"
            assert result[0].command == expected_commands[0], (
                f"Expected: {expected_commands[0]}\nGot: {result[0].command}"
            )
            assert result[1].command == expected_commands[1], (
                f"Expected: {expected_commands[1]}\nGot: {result[1].command}"
            )


def test_hevc_x265_hdr10_settings():
    """Test the build function with HDR10 settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=x265Settings(
            crf=22,
            preset="medium",
            profile="default",
            tune="default",
            hdr10=True,
            hdr10_opt=True,
            repeat_headers=True,
            aq_mode=2,
            bframes=4,
            b_adapt=2,
            frame_threads=0,
            intra_smoothing=True,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
        hdr10_metadata=True,
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", None)

        result = build(fastflix)

        # The expected command should include HDR10 settings
        expected_command = 'ffmpeg -y -i input.mkv  -x265-params "aq-mode=2:repeat-headers=1:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=1:master-display=G(0.2650,0.6900)B(0.1500,0.0600)R(0.6800,0.3200)WP(0.3127,0.3290)L(1000.0,0.0001):max-cll=1000,300:hdr10=1:chromaloc=0"   -crf:v 22 -preset:v medium   output.mkv'
        assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
        assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
        assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_hevc_x265_custom_params():
    """Test the build function with custom x265 parameters."""
    fastflix = create_fastflix_instance(
        encoder_settings=x265Settings(
            crf=22,
            preset="medium",
            profile="default",
            tune="default",
            hdr10=False,
            hdr10_opt=False,
            repeat_headers=False,
            aq_mode=2,
            bframes=4,
            b_adapt=2,
            frame_threads=0,
            intra_smoothing=True,
            bitrate=None,
            x265_params=["keyint=120", "min-keyint=60"],
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", None)

        result = build(fastflix)

        # The expected command should include the custom x265 parameters
        expected_command = 'ffmpeg -y -i input.mkv  -x265-params "keyint=120:min-keyint=60:aq-mode=2:repeat-headers=0:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=0:hdr10=0:chromaloc=0"   -crf:v 22 -preset:v medium   output.mkv'
        assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
        assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
        assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_hevc_x265_tune_profile():
    """Test the build function with tune and profile settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=x265Settings(
            crf=22,
            preset="medium",
            profile="main10",
            tune="animation",
            hdr10=False,
            hdr10_opt=False,
            repeat_headers=False,
            aq_mode=2,
            bframes=4,
            b_adapt=2,
            frame_threads=0,
            intra_smoothing=True,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", None)

        result = build(fastflix)

        # The expected command should include the tune and profile settings
        expected_command = 'ffmpeg -y -i input.mkv -tune:v animation -profile:v main10  -x265-params "aq-mode=2:repeat-headers=0:strong-intra-smoothing=1:bframes=4:b-adapt=2:frame-threads=0:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr10_opt=0:hdr10=0:chromaloc=0"   -crf:v 22 -preset:v medium   output.mkv'
        assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
        assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
        assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"
