# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.vaapi_hevc.command_builder import build
from fastflix.models.encode import VAAPIHEVCSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def test_vaapi_hevc_basic_qp():
    """Test VAAPI HEVC build with QP mode.

    This is the key test for the start_extra-as-list fix: VAAPI encoders
    pass start_extra as a list to generate_all, which previously crashed
    when generate_ffmpeg_start tried to call shlex.split() on it.
    """
    fastflix = create_fastflix_instance(
        encoder_settings=VAAPIHEVCSettings(
            qp=26,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-init_hw_device", "vaapi=hwdev:/dev/dri/renderD128", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )
        with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []

            result = build(fastflix)

            # Verify generate_all was called with start_extra as a list
            call_kwargs = mock_generate_all.call_args
            start_extra = call_kwargs.kwargs.get("start_extra") or call_kwargs[1].get("start_extra")
            assert isinstance(start_extra, list), f"start_extra should be a list, got {type(start_extra)}"
            assert "-init_hw_device" in start_extra
            assert "-hwaccel" in start_extra
            assert "vaapi" in start_extra

    assert len(result) == 1
    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-qp" in cmd
    assert "26" in cmd


def test_vaapi_hevc_with_bitrate():
    """Test VAAPI HEVC build with bitrate mode."""
    fastflix = create_fastflix_instance(
        encoder_settings=VAAPIHEVCSettings(
            qp=None,
            bitrate="6000k",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )
        with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []

            result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    assert "-b:v" in cmd
    assert "6000k" in cmd


def test_vaapi_hevc_start_extra_contains_hw_init():
    """Verify the start_extra list has the correct VAAPI hardware init options."""
    fastflix = create_fastflix_instance(
        encoder_settings=VAAPIHEVCSettings(
            vaapi_device="/dev/dri/renderD128",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], [])
        with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []

            build(fastflix)

            call_kwargs = mock_generate_all.call_args
            start_extra = call_kwargs.kwargs.get("start_extra") or call_kwargs[1].get("start_extra")

            assert start_extra == [
                "-init_hw_device",
                "vaapi=hwdev:/dev/dri/renderD128",
                "-hwaccel",
                "vaapi",
                "-hwaccel_device",
                "hwdev",
                "-hwaccel_output_format",
                "vaapi",
            ]


def test_vaapi_hevc_all_elements_are_strings():
    """Verify the final command list contains only strings."""
    fastflix = create_fastflix_instance(
        encoder_settings=VAAPIHEVCSettings(
            qp=26,
            bitrate=None,
            level="5.1",
            aud=True,
            low_power=True,
            rc_mode="CQP",
            async_depth="4",
            b_depth="2",
            idr_interval="0",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            [],
        )
        with mock.patch("fastflix.encoders.vaapi_hevc.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []

            result = build(fastflix)

    cmd = result[0].command
    assert isinstance(cmd, list)
    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"

    assert "-rc_mode" in cmd
    assert "CQP" in cmd
    assert "-level" in cmd
    assert "5.1" in cmd
    assert "-aud" in cmd
    assert "-low-power" in cmd
