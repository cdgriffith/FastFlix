# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.svt_av1.command_builder import build
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_svt_av1_single_pass_qp():
    """Test the build function with single-pass QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="crf",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=True,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the QP setting and other basic parameters
            expected_command = 'ffmpeg -y -i input.mkv -strict experimental -preset 7 --color_details  -svtav1-params "tile-columns=0:tile-rows=0:scd=0:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9"  -crf 24   output.mkv'
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_svt_av1_two_pass_qp():
    """Test the build function with two-pass QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="crf",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=False,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            # Mock the secrets.token_hex function to return a predictable result
            with mock.patch("fastflix.encoders.svt_av1.command_builder.secrets.token_hex") as mock_token_hex:
                mock_token_hex.return_value = "abcdef1234"

                result = build(fastflix)

                # The expected command should be a list of two Command objects for two-pass encoding
                expected_commands = [
                    'ffmpeg -y -i input.mkv -strict experimental -preset 7 --color_details  -svtav1-params "tile-columns=0:tile-rows=0:scd=0:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9" -passlogfile "pass_log_file_abcdef1234"  -crf 24 -pass 1  -an -r 24 -f matroska',
                    'ffmpeg -y -i input.mkv -strict experimental -preset 7 --color_details  -svtav1-params "tile-columns=0:tile-rows=0:scd=0:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9" -passlogfile "pass_log_file_abcdef1234"  -crf 24 -pass 2   output.mkv',
                ]
                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"
                assert result[0].command.startswith(expected_commands[0]), (
                    f"Expected: {expected_commands[0]}\nGot: {result[0].command}"
                )
                assert result[1].command == expected_commands[1], (
                    f"Expected: {expected_commands[1]}\nGot: {result[1].command}"
                )


def test_svt_av1_single_pass_bitrate():
    """Test the build function with single-pass bitrate settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=None,
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=True,
            bitrate="5000k",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            result = build(fastflix)

            # The expected command should include the bitrate setting
            expected_command = 'ffmpeg -y -i input.mkv -strict experimental -preset 7 --color_details  -svtav1-params "tile-columns=0:tile-rows=0:scd=0:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9"  -b:v 5000k   output.mkv'
            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
            assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"


def test_svt_av1_with_hdr():
    """Test the build function with HDR settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="crf",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=True,
            single_pass=True,
            bitrate=None,
            pix_fmt="yuv420p10le",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
        hdr10_metadata=True,
    )

    # Mock the generate_all function to return a predictable result
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = ("ffmpeg -y -i input.mkv ", " output.mkv", "-r 24")

        # Mock the generate_color_details function to return a predictable result
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = "--color_details"

            # Mock the convert_me function to return predictable results
            with mock.patch("fastflix.encoders.svt_av1.command_builder.convert_me", create=True) as mock_convert_me:
                mock_convert_me.side_effect = lambda x, y=50000: "0.0100,0.0200" if y == 50000 else "0.1000,0.0001"

                result = build(fastflix)

                # The expected command should include HDR settings
                expected_command = 'ffmpeg -y -i input.mkv -strict experimental -preset 7 --color_details  -svtav1-params "tile-columns=0:tile-rows=0:scd=1:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9:mastering-display=G(0.0000,0.0000)B(0.0000,0.0000)R(0.0000,0.0000)WP(0.0000,0.0000)L(0.1000,0.0000):content-light=1000,300:enable-hdr=1"  -crf 24   output.mkv'
                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"
                assert result[0].command == expected_command, f"Expected: {expected_command}\nGot: {result[0].command}"
