# -*- coding: utf-8 -*-
from pathlib import Path
from unittest import mock

from fastflix.encoders.common.helpers import (
    Command,
    generate_ffmpeg_start,
    generate_ending,
    generate_filters,
    generate_all,
    generate_color_details,
)
from fastflix.models.encode import x265Settings

from tests.conftest import (
    fastflix_instance,
)


def test_command_class():
    """Test the Command class."""
    # Test basic command creation
    cmd = Command(command='ffmpeg -i "input.mkv" output.mp4', name="Test Command", exe="ffmpeg")
    assert cmd.command == 'ffmpeg -i "input.mkv" output.mp4'
    assert cmd.name == "Test Command"
    assert cmd.exe == "ffmpeg"
    assert cmd.item == "command"
    assert cmd.shell is False
    assert cmd.uuid is not None


def test_generate_ffmpeg_start_basic(fastflix_instance):
    """Test the generate_ffmpeg_start function with basic parameters."""
    result = generate_ffmpeg_start(
        source=Path(r"C:\test_  file.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
    )

    expected = r'"ffmpeg" -y -i "C:\test_  file.mkv" -map 0:0 -c:v libx265 -pix_fmt yuv420p10le '
    assert result == expected


def test_generate_ffmpeg_start_with_options(fastflix_instance):
    """Test the generate_ffmpeg_start function with various options."""
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
        start_time=10,
        end_time=60,
        fast_seek=True,
        video_title="Test Video",
        video_track_title="Main Track",
        maxrate=5000,
        bufsize=10000,
        source_fps="24",
        vsync="cfr",
        enable_opencl=True,
        remove_hdr=True,
        start_extra="--extra-option",
    )

    expected = '"ffmpeg" --extra-option -init_hw_device opencl:0.0=ocl -filter_hw_device ocl -y -ss 10 -to 60 -r 24 -i "input.mkv" -metadata title="Test Video" -map 0:0 -fps_mode cfr -c:v libx265 -pix_fmt yuv420p10le -maxrate:v 5000k -bufsize:v 10000k -metadata:s:v:0 title="Main Track" '
    assert result == expected


def test_generate_ending_basic():
    """Test the generate_ending function with basic parameters."""
    ending, output_fps = generate_ending(
        audio="",
        subtitles="",
        output_video=Path("output.mkv"),
    )

    expected = ' -map_metadata -1 -map_chapters 0 "output.mkv"'
    assert ending == expected
    assert output_fps == ""


def test_generate_ending_with_options():
    """Test the generate_ending function with various options."""
    ending, output_fps = generate_ending(
        audio="-map 0:1 -c:a copy",
        subtitles="-map 0:2 -c:s copy",
        cover="-attach cover.jpg",
        output_video=Path("output.mkv"),
        copy_chapters=False,
        remove_metadata=False,
        output_fps="24",
        disable_rotate_metadata=False,
        copy_data=True,
    )

    expected = ' -metadata:s:v rotate=0 -map_metadata 0 -map_chapters -1 -r 24 -map 0:1 -c:a copy -map 0:2 -c:s copy -attach cover.jpg -map 0:d -c:d copy "output.mkv"'
    assert ending == expected
    assert output_fps == "-r 24"


def test_generate_filters_basic():
    """Test the generate_filters function with basic parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
    )

    # With no filters specified, should return empty string
    assert result == ""


def test_generate_filters_with_crop():
    """Test the generate_filters function with crop parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        crop={"width": 1920, "height": 1080, "left": 0, "top": 0},
    )

    expected = ' -filter_complex "[0:0]crop=1920:1080:0:0[v]" -map "[v]" '
    assert result == expected


def test_generate_filters_with_scale():
    """Test the generate_filters function with scale parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        scale="1920:-8",
    )

    expected = ' -filter_complex "[0:0]scale=1920:-8:flags=lanczos,setsar=1:1[v]" -map "[v]" '
    assert result == expected


def test_generate_filters_with_hdr_removal():
    """Test the generate_filters function with HDR removal."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        remove_hdr=True,
        tone_map="hable",
    )

    expected = ' -filter_complex "[0:0]zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p[v]" -map "[v]" '
    assert result == expected


def test_generate_filters_with_multiple_options():
    """Test the generate_filters function with multiple options."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        crop={"width": 1920, "height": 1080, "left": 0, "top": 0},
        scale="1920:-8",
        rotate=1,
        deinterlace=True,
        brightness="0.1",
        contrast="1.1",
        saturation="1.2",
        video_speed=0.5,
    )

    expected = ' -filter_complex "[0:0]yadif,crop=1920:1080:0:0,scale=1920:-8:flags=lanczos,setsar=1:1,transpose=1,setpts=0.5*PTS,eq=eval=frame:brightness=0.1:saturation=1.2:contrast=1.1[v]" -map "[v]" '
    assert result == expected


def test_generate_all(fastflix_instance):
    """Test the generate_all function."""
    # Mock the component functions to isolate the test
    with (
        mock.patch("fastflix.encoders.common.helpers.build_audio") as mock_build_audio,
        mock.patch("fastflix.encoders.common.helpers.build_subtitle") as mock_build_subtitle,
        mock.patch("fastflix.encoders.common.helpers.build_attachments") as mock_build_attachments,
        mock.patch("fastflix.encoders.common.helpers.generate_filters") as mock_generate_filters,
        mock.patch("fastflix.encoders.common.helpers.generate_ending") as mock_generate_ending,
        mock.patch("fastflix.encoders.common.helpers.generate_ffmpeg_start") as mock_generate_ffmpeg_start,
    ):

        # Set up the mock returns
        mock_build_audio.return_value = "-map 0:1 -c:a copy"
        mock_build_subtitle.return_value = ("-map 0:2 -c:s copy", None, None)
        mock_build_attachments.return_value = "-attach cover.jpg"
        mock_generate_filters.return_value = "-filter_complex [0:0]scale=1920:-8[v] -map [v]"
        mock_generate_ending.return_value = (' -map_metadata -1 "output.mkv"', "-r 24")
        mock_generate_ffmpeg_start.return_value = 'ffmpeg -y -i "input.mkv"'

        # Set up the video encoder settings
        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        # Call the function
        beginning, ending, output_fps = generate_all(fastflix_instance, "libx265")

        # Check the results
        assert beginning == 'ffmpeg -y -i "input.mkv"'
        assert ending == ' -map_metadata -1 "output.mkv"'
        assert output_fps == "-r 24"

        # Verify the mock calls
        mock_build_audio.assert_called_once_with(fastflix_instance.current_video.audio_tracks)
        mock_build_subtitle.assert_called_once_with(fastflix_instance.current_video.subtitle_tracks)
        mock_build_attachments.assert_called_once_with(fastflix_instance.current_video.attachment_tracks)


def test_generate_color_details(fastflix_instance):
    """Test the generate_color_details function."""
    # Test with HDR removal enabled
    fastflix_instance.current_video.video_settings.remove_hdr = True
    result = generate_color_details(fastflix_instance)
    assert result == ""

    # Test with HDR removal disabled and color settings
    fastflix_instance.current_video.video_settings.remove_hdr = False
    fastflix_instance.current_video.video_settings.color_primaries = "bt2020"
    fastflix_instance.current_video.video_settings.color_transfer = "smpte2084"
    fastflix_instance.current_video.video_settings.color_space = "bt2020nc"

    result = generate_color_details(fastflix_instance)
    expected = "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"
    assert result == expected
