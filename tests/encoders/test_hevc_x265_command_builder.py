# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.hevc_x265.command_builder import build
from fastflix.encoders.common.helpers import null
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

    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )

        result = build(fastflix)

        assert isinstance(result, list)
        assert len(result) == 1
        cmd = result[0].command
        assert isinstance(cmd, list)
        assert "-x265-params" in cmd
        assert "-crf:v" in cmd
        assert "22" in cmd
        assert "-preset:v" in cmd
        assert "medium" in cmd

        # Verify x265 params contain expected values
        params_idx = cmd.index("-x265-params")
        params_str = cmd[params_idx + 1]
        assert "aq-mode=2" in params_str
        assert "bframes=4" in params_str
        assert "colorprim=bt2020" in params_str


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

    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )
        with mock.patch("fastflix.encoders.hevc_x265.command_builder.secrets.token_hex") as mock_token_hex:
            mock_token_hex.return_value = "abcdef1234"

            result = build(fastflix)

            assert isinstance(result, list)
            assert len(result) == 2

            # First pass
            cmd1 = result[0].command
            assert isinstance(cmd1, list)
            assert "-b:v" in cmd1
            assert "5000k" in cmd1
            assert "-an" in cmd1
            assert "-sn" in cmd1
            assert null in cmd1
            params_idx = cmd1.index("-x265-params")
            assert "pass=1" in cmd1[params_idx + 1]

            # Second pass
            cmd2 = result[1].command
            assert isinstance(cmd2, list)
            assert "-b:v" in cmd2
            assert "5000k" in cmd2
            assert "output.mkv" in cmd2
            params_idx = cmd2.index("-x265-params")
            assert "pass=2" in cmd2[params_idx + 1]


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

    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )

        result = build(fastflix)

        assert isinstance(result, list)
        assert len(result) == 1
        cmd = result[0].command
        assert isinstance(cmd, list)

        params_idx = cmd.index("-x265-params")
        params_str = cmd[params_idx + 1]
        assert "hdr10_opt=1" in params_str
        assert "hdr10=1" in params_str
        assert "master-display=" in params_str
        assert "max-cll=1000,300" in params_str


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

    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )

        result = build(fastflix)

        assert isinstance(result, list)
        assert len(result) == 1
        cmd = result[0].command
        assert isinstance(cmd, list)

        params_idx = cmd.index("-x265-params")
        params_str = cmd[params_idx + 1]
        assert "keyint=120" in params_str
        assert "min-keyint=60" in params_str


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

    with mock.patch("fastflix.encoders.hevc_x265.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )

        result = build(fastflix)

        assert isinstance(result, list)
        assert len(result) == 1
        cmd = result[0].command
        assert isinstance(cmd, list)
        assert "-tune:v" in cmd
        assert "animation" in cmd
        assert "-profile:v" in cmd
        assert "main10" in cmd
