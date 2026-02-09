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


def test_command_class():
    """Test the Command class with string and list commands."""
    # Test string command creation
    cmd = Command(command='ffmpeg -i "input.mkv" output.mp4', name="Test Command", exe="ffmpeg")
    assert cmd.command == 'ffmpeg -i "input.mkv" output.mp4'
    assert cmd.name == "Test Command"
    assert cmd.exe == "ffmpeg"
    assert cmd.item == "command"
    assert cmd.shell is False
    assert cmd.uuid is not None

    # Test list command creation
    cmd_list = Command(command=["ffmpeg", "-i", "input.mkv", "output.mp4"], name="List Command", exe="ffmpeg")
    assert cmd_list.command == ["ffmpeg", "-i", "input.mkv", "output.mp4"]
    assert isinstance(cmd_list.to_list(), list)
    assert isinstance(cmd_list.to_string(), str)


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

    assert isinstance(result, list)
    assert result[0] == "ffmpeg"
    assert "-y" in result
    assert "-i" in result
    assert r"C:\test_  file.mkv" in result
    assert "-map" in result
    assert "0:0" in result
    assert "-c:v" in result
    assert "libx265" in result
    assert "-pix_fmt" in result
    assert "yuv420p10le" in result


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

    assert isinstance(result, list)
    assert result[0] == "ffmpeg"
    assert "--extra-option" in result
    assert "-init_hw_device" in result
    assert "-ss" in result
    assert "10" in result
    assert "-to" in result
    assert "60" in result
    assert "-r" in result
    assert "24" in result
    assert "-metadata" in result
    assert "title=Test Video" in result
    assert "-fps_mode" in result
    assert "cfr" in result
    assert "-maxrate:v" in result
    assert "5000k" in result
    assert "-bufsize:v" in result
    assert "10000k" in result
    assert "-metadata:s:v:0" in result
    assert "title=Main Track" in result


def test_generate_ffmpeg_start_with_list_start_extra(fastflix_instance):
    """Test generate_ffmpeg_start with start_extra as a list (VAAPI-style).

    VAAPI encoders pass start_extra as a list of hardware init options.
    Previously this crashed because shlex.split() was called on the list.
    """
    start_extra_list = [
        "-init_hw_device",
        "vaapi=hwdev:/dev/dri/renderD128",
        "-hwaccel",
        "vaapi",
        "-hwaccel_device",
        "hwdev",
        "-hwaccel_output_format",
        "vaapi",
    ]
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="hevc_vaapi",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="vaapi",
        start_extra=start_extra_list,
    )

    assert isinstance(result, list)
    # All start_extra elements should appear in the command
    assert "-init_hw_device" in result
    assert "vaapi=hwdev:/dev/dri/renderD128" in result
    assert "-hwaccel" in result
    assert "vaapi" in result
    assert "-hwaccel_device" in result
    assert "hwdev" in result
    assert "-hwaccel_output_format" in result
    # start_extra should come before -y
    init_idx = result.index("-init_hw_device")
    y_idx = result.index("-y")
    assert init_idx < y_idx


def test_generate_ffmpeg_start_with_empty_list_start_extra(fastflix_instance):
    """Test generate_ffmpeg_start with start_extra as an empty list."""
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
        start_extra=[],
    )

    assert isinstance(result, list)
    assert result[0] == "ffmpeg"
    assert "-y" in result


def test_generate_ffmpeg_start_numeric_times_are_strings(fastflix_instance):
    """Test that numeric start_time and end_time values are converted to strings."""
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
        start_time=10.5,
        end_time=120.0,
    )

    assert isinstance(result, list)
    for i, element in enumerate(result):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"
    assert "-ss" in result
    assert "10.5" in result
    assert "-to" in result
    assert "120.0" in result


def test_generate_ending_basic():
    """Test the generate_ending function with basic parameters."""
    ending, output_fps = generate_ending(
        audio=[],
        subtitles=[],
        output_video=Path("output.mkv"),
    )

    assert isinstance(ending, list)
    assert "-map_metadata" in ending
    assert "-1" in ending
    assert "-map_chapters" in ending
    assert "0" in ending
    assert "output.mkv" in ending
    assert output_fps == []


def test_generate_ending_with_options():
    """Test the generate_ending function with various options."""
    ending, output_fps = generate_ending(
        audio=["-map", "0:1", "-c:a", "copy"],
        subtitles=["-map", "0:2", "-c:s", "copy"],
        cover=["-attach", "cover.jpg"],
        output_video=Path("output.mkv"),
        copy_chapters=False,
        remove_metadata=False,
        output_fps="24",
        disable_rotate_metadata=False,
        copy_data=True,
    )

    assert isinstance(ending, list)
    assert "-metadata:s:v" in ending
    assert "rotate=0" in ending
    assert "-map_metadata" in ending
    assert "0" in ending
    assert "-map_chapters" in ending
    assert "-1" in ending
    assert "-r" in ending
    assert "24" in ending
    assert "-map" in ending
    assert "0:1" in ending
    assert "-c:a" in ending
    assert "copy" in ending
    assert "-attach" in ending
    assert "cover.jpg" in ending
    assert "0:d" in ending
    assert "-c:d" in ending
    assert "output.mkv" in ending
    assert output_fps == ["-r", "24"]


def test_generate_filters_basic():
    """Test the generate_filters function with basic parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
    )

    # With no filters specified, should return empty list
    assert result == []


def test_generate_filters_with_crop():
    """Test the generate_filters function with crop parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        crop={"width": 1920, "height": 1080, "left": 0, "top": 0},
    )

    assert isinstance(result, list)
    assert len(result) == 4
    assert result[0] == "-filter_complex"
    assert "[0:0]crop=1920:1080:0:0[v]" in result[1]
    assert result[2] == "-map"
    assert result[3] == "[v]"


def test_generate_filters_with_scale():
    """Test the generate_filters function with scale parameters."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        scale="1920:-8",
    )

    assert isinstance(result, list)
    assert result[0] == "-filter_complex"
    assert "scale=1920:-8:flags=lanczos,setsar=1:1" in result[1]
    assert result[2] == "-map"
    assert result[3] == "[v]"


def test_generate_filters_with_hdr_removal():
    """Test the generate_filters function with HDR removal."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        remove_hdr=True,
        tone_map="hable",
    )

    assert isinstance(result, list)
    assert result[0] == "-filter_complex"
    assert "tonemap=tonemap=hable" in result[1]
    assert result[2] == "-map"
    assert result[3] == "[v]"


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

    assert isinstance(result, list)
    assert result[0] == "-filter_complex"
    filter_str = result[1]
    assert "yadif" in filter_str
    assert "crop=1920:1080:0:0" in filter_str
    assert "scale=1920:-8:flags=lanczos,setsar=1:1" in filter_str
    assert "transpose=1" in filter_str
    assert "setpts=0.5*PTS" in filter_str
    assert "brightness=0.1" in filter_str
    assert "saturation=1.2" in filter_str
    assert "contrast=1.1" in filter_str
    assert result[2] == "-map"
    assert result[3] == "[v]"


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
        # Set up the mock returns as lists
        mock_build_audio.return_value = ["-map", "0:1", "-c:a", "copy"]
        mock_build_subtitle.return_value = (["-map", "0:2", "-c:s", "copy"], None, None)
        mock_build_attachments.return_value = ["-attach", "cover.jpg"]
        mock_generate_filters.return_value = ["-filter_complex", "[0:0]scale=1920:-8[v]", "-map", "[v]"]
        mock_generate_ending.return_value = (["-map_metadata", "-1", "output.mkv"], ["-r", "24"])
        mock_generate_ffmpeg_start.return_value = ["ffmpeg", "-y", "-i", "input.mkv"]

        # Set up the video encoder settings
        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        # Call the function
        beginning, ending, output_fps = generate_all(fastflix_instance, "libx265")

        # Check the results
        assert beginning == ["ffmpeg", "-y", "-i", "input.mkv"]
        assert ending == ["-map_metadata", "-1", "output.mkv"]
        assert output_fps == ["-r", "24"]

        # Verify the mock calls
        mock_build_audio.assert_called_once_with(fastflix_instance.current_video.audio_tracks)
        mock_build_subtitle.assert_called_once_with(
            fastflix_instance.current_video.subtitle_tracks,
            output_path=fastflix_instance.current_video.video_settings.output_path,
        )
        mock_build_attachments.assert_called_once_with(fastflix_instance.current_video.attachment_tracks)


def test_generate_all_with_list_start_extra(fastflix_instance):
    """Test generate_all passes list start_extra through to generate_ffmpeg_start.

    VAAPI encoders pass start_extra as a list. This test verifies the parameter
    is forwarded correctly without being mangled by shlex.split().
    """
    with (
        mock.patch("fastflix.encoders.common.helpers.build_audio") as mock_build_audio,
        mock.patch("fastflix.encoders.common.helpers.build_subtitle") as mock_build_subtitle,
        mock.patch("fastflix.encoders.common.helpers.build_attachments") as mock_build_attachments,
        mock.patch("fastflix.encoders.common.helpers.generate_filters") as mock_generate_filters,
        mock.patch("fastflix.encoders.common.helpers.generate_ending") as mock_generate_ending,
        mock.patch("fastflix.encoders.common.helpers.generate_ffmpeg_start") as mock_generate_ffmpeg_start,
    ):
        mock_build_audio.return_value = []
        mock_build_subtitle.return_value = ([], None, None)
        mock_build_attachments.return_value = []
        mock_generate_filters.return_value = []
        mock_generate_ending.return_value = (["output.mkv"], [])
        mock_generate_ffmpeg_start.return_value = ["ffmpeg", "-y", "-i", "input.mkv"]

        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        vaapi_start_extra = [
            "-init_hw_device",
            "vaapi=hwdev:/dev/dri/renderD128",
            "-hwaccel",
            "vaapi",
        ]

        generate_all(fastflix_instance, "hevc_vaapi", start_extra=vaapi_start_extra)

        # Verify start_extra was passed as-is (list, not string)
        call_kwargs = mock_generate_ffmpeg_start.call_args
        assert call_kwargs.kwargs["start_extra"] == vaapi_start_extra


def test_generate_ffmpeg_start_with_extra_inputs(fastflix_instance):
    """Test generate_ffmpeg_start with extra -i inputs for external subtitles."""
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
        extra_inputs=["-i", "/path/to/subs.srt", "-i", "/path/to/subs2.ass"],
    )

    assert isinstance(result, list)
    # Extra inputs should appear after the primary -i source
    i_indices = [i for i, x in enumerate(result) if x == "-i"]
    assert len(i_indices) == 3  # primary + 2 external
    # Primary source comes first
    assert result[i_indices[0] + 1] == "input.mkv"
    # External subs come after
    assert result[i_indices[1] + 1] == "/path/to/subs.srt"
    assert result[i_indices[2] + 1] == "/path/to/subs2.ass"


def test_generate_ffmpeg_start_no_extra_inputs(fastflix_instance):
    """Test generate_ffmpeg_start without extra_inputs (default behavior)."""
    result = generate_ffmpeg_start(
        source=Path("input.mkv"),
        ffmpeg=Path("ffmpeg"),
        encoder="libx265",
        selected_track=0,
        ffmpeg_version="n5.0",
        pix_fmt="yuv420p10le",
    )

    # Only one -i for the primary source
    i_indices = [i for i, x in enumerate(result) if x == "-i"]
    assert len(i_indices) == 1


def test_generate_filters_with_external_burn_in_picture():
    """Test generate_filters with burn_in_file_index for picture-based external subtitle."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        burn_in_subtitle_track=0,
        burn_in_subtitle_type="picture",
        burn_in_file_index=1,
    )

    assert isinstance(result, list)
    assert result[0] == "-filter_complex"
    # Should reference file index 1 for the subtitle overlay
    assert "[1:0]" in result[1]
    assert "[0:0]" in result[1]
    assert "overlay" in result[1]


def test_generate_filters_burn_in_file_index_default():
    """Test generate_filters defaults burn_in_file_index=0 for embedded tracks."""
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        burn_in_subtitle_track=2,
        burn_in_subtitle_type="picture",
    )

    assert isinstance(result, list)
    assert result[0] == "-filter_complex"
    # Should reference file index 0 (default)
    assert "[0:0][0:2]overlay" in result[1]


def test_generate_all_with_external_subtitles(fastflix_instance):
    """Test generate_all collects external subtitle file paths and builds extra -i inputs."""
    from fastflix.models.encode import SubtitleTrack

    # Add an external subtitle track
    fastflix_instance.current_video.subtitle_tracks.append(
        SubtitleTrack(
            index=0,
            outdex=4,
            language="fre",
            subtitle_type="text",
            enabled=True,
            burn_in=False,
            long_name="[EXT] french.srt",
            external=True,
            file_path="/path/to/french.srt",
        )
    )

    with (
        mock.patch("fastflix.encoders.common.helpers.build_audio") as mock_build_audio,
        mock.patch("fastflix.encoders.common.helpers.build_subtitle") as mock_build_subtitle,
        mock.patch("fastflix.encoders.common.helpers.build_attachments") as mock_build_attachments,
        mock.patch("fastflix.encoders.common.helpers.generate_filters") as mock_generate_filters,
        mock.patch("fastflix.encoders.common.helpers.generate_ending") as mock_generate_ending,
        mock.patch("fastflix.encoders.common.helpers.generate_ffmpeg_start") as mock_generate_ffmpeg_start,
    ):
        mock_build_audio.return_value = []
        mock_build_subtitle.return_value = ([], None, None)
        mock_build_attachments.return_value = []
        mock_generate_filters.return_value = []
        mock_generate_ending.return_value = (["output.mkv"], [])
        mock_generate_ffmpeg_start.return_value = ["ffmpeg", "-y", "-i", "input.mkv"]

        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        generate_all(fastflix_instance, "libx265")

        # Verify extra_inputs was passed with the external subtitle file
        call_kwargs = mock_generate_ffmpeg_start.call_args
        assert call_kwargs.kwargs["extra_inputs"] == ["-i", "/path/to/french.srt"]

        # Verify external track got file_index=1 assigned
        ext_track = fastflix_instance.current_video.subtitle_tracks[-1]
        assert ext_track.file_index == 1


def test_generate_all_external_subs_fast_seek_includes_ss(fastflix_instance):
    """Test that external subtitle inputs get -ss/-to when fast seek is used with a start time.

    Without this, external subtitle timing is wrong because the primary video is seeked
    but the external subtitle input starts from the beginning of the file.
    """
    from fastflix.models.encode import SubtitleTrack

    # Set up fast seek with start/end times
    fastflix_instance.current_video.video_settings.fast_seek = True
    fastflix_instance.current_video.video_settings.start_time = 300
    fastflix_instance.current_video.video_settings.end_time = 600

    # Add an external subtitle track
    fastflix_instance.current_video.subtitle_tracks.append(
        SubtitleTrack(
            index=0,
            outdex=4,
            language="fre",
            subtitle_type="text",
            enabled=True,
            burn_in=False,
            long_name="[EXT] french.srt",
            external=True,
            file_path="/path/to/french.srt",
        )
    )

    with (
        mock.patch("fastflix.encoders.common.helpers.build_audio") as mock_build_audio,
        mock.patch("fastflix.encoders.common.helpers.build_subtitle") as mock_build_subtitle,
        mock.patch("fastflix.encoders.common.helpers.build_attachments") as mock_build_attachments,
        mock.patch("fastflix.encoders.common.helpers.generate_filters") as mock_generate_filters,
        mock.patch("fastflix.encoders.common.helpers.generate_ending") as mock_generate_ending,
        mock.patch("fastflix.encoders.common.helpers.generate_ffmpeg_start") as mock_generate_ffmpeg_start,
    ):
        mock_build_audio.return_value = []
        mock_build_subtitle.return_value = ([], None, None)
        mock_build_attachments.return_value = []
        mock_generate_filters.return_value = []
        mock_generate_ending.return_value = (["output.mkv"], [])
        mock_generate_ffmpeg_start.return_value = ["ffmpeg", "-y", "-ss", "300", "-to", "600", "-i", "input.mkv"]

        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        generate_all(fastflix_instance, "libx265")

        # Verify extra_inputs includes -ss and -to before the external -i
        call_kwargs = mock_generate_ffmpeg_start.call_args
        extra_inputs = call_kwargs.kwargs["extra_inputs"]
        assert extra_inputs == ["-ss", "300", "-to", "600", "-i", "/path/to/french.srt"]


def test_generate_all_external_subs_exact_seek_no_ss_in_extra(fastflix_instance):
    """Test that external subtitle inputs do NOT get -ss/-to when exact seek (non-fast) is used.

    With exact seek, -ss is placed after all inputs as an output option, applying globally.
    """
    from fastflix.models.encode import SubtitleTrack

    # Set up exact seek with start/end times
    fastflix_instance.current_video.video_settings.fast_seek = False
    fastflix_instance.current_video.video_settings.start_time = 300
    fastflix_instance.current_video.video_settings.end_time = 600

    # Add an external subtitle track
    fastflix_instance.current_video.subtitle_tracks.append(
        SubtitleTrack(
            index=0,
            outdex=4,
            language="fre",
            subtitle_type="text",
            enabled=True,
            burn_in=False,
            long_name="[EXT] french.srt",
            external=True,
            file_path="/path/to/french.srt",
        )
    )

    with (
        mock.patch("fastflix.encoders.common.helpers.build_audio") as mock_build_audio,
        mock.patch("fastflix.encoders.common.helpers.build_subtitle") as mock_build_subtitle,
        mock.patch("fastflix.encoders.common.helpers.build_attachments") as mock_build_attachments,
        mock.patch("fastflix.encoders.common.helpers.generate_filters") as mock_generate_filters,
        mock.patch("fastflix.encoders.common.helpers.generate_ending") as mock_generate_ending,
        mock.patch("fastflix.encoders.common.helpers.generate_ffmpeg_start") as mock_generate_ffmpeg_start,
    ):
        mock_build_audio.return_value = []
        mock_build_subtitle.return_value = ([], None, None)
        mock_build_attachments.return_value = []
        mock_generate_filters.return_value = []
        mock_generate_ending.return_value = (["output.mkv"], [])
        mock_generate_ffmpeg_start.return_value = ["ffmpeg", "-y", "-i", "input.mkv"]

        fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()

        generate_all(fastflix_instance, "libx265")

        # With exact seek, extra_inputs should only have -i (no -ss/-to)
        call_kwargs = mock_generate_ffmpeg_start.call_args
        extra_inputs = call_kwargs.kwargs["extra_inputs"]
        assert extra_inputs == ["-i", "/path/to/french.srt"]


def test_generate_color_details(fastflix_instance):
    """Test the generate_color_details function."""
    # Test with HDR removal enabled
    fastflix_instance.current_video.video_settings.remove_hdr = True
    result = generate_color_details(fastflix_instance)
    assert result == []

    # Test with HDR removal disabled and color settings
    fastflix_instance.current_video.video_settings.remove_hdr = False
    fastflix_instance.current_video.video_settings.color_primaries = "bt2020"
    fastflix_instance.current_video.video_settings.color_transfer = "smpte2084"
    fastflix_instance.current_video.video_settings.color_space = "bt2020nc"

    result = generate_color_details(fastflix_instance)
    assert result == ["-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"]
