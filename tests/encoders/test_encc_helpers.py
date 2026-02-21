# -*- coding: utf-8 -*-
from unittest import mock
from box import Box
import pytest

from fastflix.encoders.common.encc_helpers import (
    audio_quality_converter,
    rigaya_avformat_reader,
    rigaya_auto_options,
    rigaya_trim_or_seek,
    _parse_frame_rate,
    pa_builder,
    get_stream_pos,
    build_audio,
    build_subtitle,
)
from fastflix.models.encode import VCEEncCSettings


@pytest.fixture
def encc_fastflix_instance(fastflix_instance):
    """
    Fixture providing a FastFlix instance with VCEEncCSettings initialized for testing.

    Args:
        fastflix_instance: Base FastFlix instance from conftest.py

    Returns:
        A FastFlix instance with video_encoder_settings initialized
    """
    # Initialize the video_encoder_settings with VCEEncCSettings
    fastflix_instance.current_video.video_settings.video_encoder_settings = VCEEncCSettings(
        decoder="Auto",
        preset="slow",
        bitrate="5000k",
    )
    return fastflix_instance


def test_audio_quality_converter_libopus():
    """Test the audio_quality_converter function with libopus codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libopus", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?240k "

    result = audio_quality_converter(5, "libopus", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?48k "

    # Test with different channel counts
    result = audio_quality_converter(0, "libopus", channels=6, track_number=1)
    assert result == " --audio-bitrate 1?720k "


def test_audio_quality_converter_aac():
    """Test the audio_quality_converter function with aac codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?2 "

    result = audio_quality_converter(5, "aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?1 "

    result = audio_quality_converter(9, "aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?0.2 "


def test_audio_quality_converter_libfdk_aac():
    """Test the audio_quality_converter function with libfdk_aac codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libfdk_aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?1 "

    result = audio_quality_converter(5, "libfdk_aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?3 "

    result = audio_quality_converter(9, "libfdk_aac", channels=2, track_number=1)
    assert result == " --audio-quality 1?5 "


def test_audio_quality_converter_libvorbis():
    """Test the audio_quality_converter function with libvorbis codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libvorbis", channels=2, track_number=1)
    assert result == " --audio-quality 1?10 "

    result = audio_quality_converter(5, "libvorbis", channels=2, track_number=1)
    assert result == " --audio-quality 1?5 "

    result = audio_quality_converter(9, "libvorbis", channels=2, track_number=1)
    assert result == " --audio-quality 1?1 "

    # Test with vorbis alias
    result = audio_quality_converter(0, "vorbis", channels=2, track_number=1)
    assert result == " --audio-quality 1?10 "


def test_audio_quality_converter_mp3():
    """Test the audio_quality_converter function with mp3 codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libmp3lame", channels=2, track_number=1)
    assert result == " --audio-quality 1?0 "

    result = audio_quality_converter(5, "libmp3lame", channels=2, track_number=1)
    assert result == " --audio-quality 1?5 "

    # Test with mp3 alias
    result = audio_quality_converter(0, "mp3", channels=2, track_number=1)
    assert result == " --audio-quality 1?0 "


def test_audio_quality_converter_ac3():
    """Test the audio_quality_converter function with ac3 codec."""
    # Test with different quality levels and channel counts
    result = audio_quality_converter(0, "ac3", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?960k "

    result = audio_quality_converter(5, "ac3", channels=6, track_number=1)
    assert result == " --audio-bitrate 1?576k "

    # Test with eac3
    result = audio_quality_converter(0, "eac3", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?960k "

    # Test with truehd
    result = audio_quality_converter(0, "truehd", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?960k "


def test_audio_quality_converter_default():
    """Test the audio_quality_converter function with default fallback."""
    # Test with an unknown codec
    result = audio_quality_converter(0, "unknown_codec", channels=2, track_number=1)
    assert result == " --audio-bitrate 1?240k "

    result = audio_quality_converter(5, "unknown_codec", channels=6, track_number=1)
    assert result == " --audio-bitrate 1?144k "


def test_rigaya_avformat_reader_avs(encc_fastflix_instance):
    """Test the rigaya_avformat_reader function with AVS file."""
    # Set up the test
    encc_fastflix_instance.current_video.source = encc_fastflix_instance.current_video.source.with_suffix(".avs")
    encc_fastflix_instance.current_video.video_settings.video_encoder_settings.decoder = "Auto"

    # Test the function
    result = rigaya_avformat_reader(encc_fastflix_instance)
    assert result == []


def test_rigaya_avformat_reader_vpy(encc_fastflix_instance):
    """Test the rigaya_avformat_reader function with VPY file."""
    # Set up the test
    encc_fastflix_instance.current_video.source = encc_fastflix_instance.current_video.source.with_suffix(".vpy")
    encc_fastflix_instance.current_video.video_settings.video_encoder_settings.decoder = "Auto"

    # Test the function
    result = rigaya_avformat_reader(encc_fastflix_instance)
    assert result == []


def test_rigaya_avformat_reader_hardware(encc_fastflix_instance):
    """Test the rigaya_avformat_reader function with hardware decoder."""
    # Set up the test
    encc_fastflix_instance.current_video.source = encc_fastflix_instance.current_video.source.with_suffix(".mkv")
    encc_fastflix_instance.current_video.video_settings.video_encoder_settings.decoder = "Hardware"

    # Test the function
    result = rigaya_avformat_reader(encc_fastflix_instance)
    assert result == ["--avhw"]


def test_rigaya_avformat_reader_software(encc_fastflix_instance):
    """Test the rigaya_avformat_reader function with software decoder."""
    # Set up the test
    encc_fastflix_instance.current_video.source = encc_fastflix_instance.current_video.source.with_suffix(".mkv")
    encc_fastflix_instance.current_video.video_settings.video_encoder_settings.decoder = "Software"

    # Test the function
    result = rigaya_avformat_reader(encc_fastflix_instance)
    assert result == ["--avsw"]


def test_rigaya_auto_options_with_reader(encc_fastflix_instance):
    """Test the rigaya_auto_options function with a reader format."""
    # Set up the test
    with mock.patch("fastflix.encoders.common.encc_helpers.rigaya_avformat_reader") as mock_reader:
        mock_reader.return_value = ["--avhw"]

        # Set color settings
        encc_fastflix_instance.current_video.video_settings.color_space = "bt2020nc"
        encc_fastflix_instance.current_video.video_settings.color_transfer = "smpte2084"
        encc_fastflix_instance.current_video.video_settings.color_primaries = "bt2020"

        # Test the function
        result = rigaya_auto_options(encc_fastflix_instance)

        # Check that auto options are included as consecutive list elements
        assert "--chromaloc" in result and "auto" in result
        assert "--colorrange" in result
        assert "--colormatrix" in result and "bt2020nc" in result
        assert "--transfer" in result and "smpte2084" in result
        assert "--colorprim" in result and "bt2020" in result


def test_rigaya_auto_options_without_reader(encc_fastflix_instance):
    """Test the rigaya_auto_options function without a reader format."""
    # Set up the test
    with mock.patch("fastflix.encoders.common.encc_helpers.rigaya_avformat_reader") as mock_reader:
        mock_reader.return_value = []

        # Set color settings
        encc_fastflix_instance.current_video.video_settings.color_space = "bt2020nc"
        encc_fastflix_instance.current_video.video_settings.color_transfer = "smpte2084"
        encc_fastflix_instance.current_video.video_settings.color_primaries = "bt2020"

        # Test the function
        result = rigaya_auto_options(encc_fastflix_instance)

        # Check that only specific color options are included
        assert "--colormatrix" in result and "bt2020nc" in result
        assert "--transfer" in result and "smpte2084" in result
        assert "--colorprim" in result and "bt2020" in result
        assert "--chromaloc" not in result
        assert "--colorrange" not in result


def test_pa_builder_disabled():
    """Test the pa_builder function with pre-analysis disabled."""
    # Create settings with pre-analysis disabled
    settings = VCEEncCSettings(
        pre_analysis=False, pa_sc="medium", pa_ss="high", pa_activity_type="y", pa_caq_strength="medium", pa_ltr=True
    )

    # Test the function
    result = pa_builder(settings)
    assert result == ""


def test_pa_builder_basic():
    """Test the pa_builder function with basic settings."""
    # Create settings with pre-analysis enabled
    settings = VCEEncCSettings(
        pre_analysis=True, pa_sc="medium", pa_ss="high", pa_activity_type="y", pa_caq_strength="medium", pa_ltr=True
    )

    # Test the function
    result = pa_builder(settings)
    assert result == "--pa sc=medium,ss=high,activity-type=y,caq-strength=medium,ltr=true,fskip-maxqp=35"


def test_pa_builder_with_optional_params():
    """Test the pa_builder function with optional parameters."""
    # Create settings with pre-analysis enabled and optional parameters
    settings = VCEEncCSettings(
        pre_analysis=True,
        pa_sc="medium",
        pa_ss="high",
        pa_activity_type="y",
        pa_caq_strength="medium",
        pa_ltr=True,
        pa_initqpsc=22,
        pa_lookahead=30,
        pa_fskip_maxqp=35,
        pa_paq="medium",
        pa_taq=1,
        pa_motion_quality="high",
    )

    # Test the function
    result = pa_builder(settings)
    assert "sc=medium" in result
    assert "ss=high" in result
    assert "activity-type=y" in result
    assert "caq-strength=medium" in result
    assert "ltr=true" in result
    assert "initqpsc=22" in result
    assert "lookahead=30" in result
    assert "fskip-maxqp=35" in result
    assert "paq=medium" in result
    assert "taq=1" in result
    assert "motion-quality=high" in result


def test_get_stream_pos():
    """Test the get_stream_pos function."""
    # Create a list of streams
    streams = [Box({"index": 0}), Box({"index": 2}), Box({"index": 5})]

    # Test the function
    result = get_stream_pos(streams)
    assert result == {0: 1, 2: 2, 5: 3}


def test_build_audio_empty():
    """Test the build_audio function with an empty list."""
    result = build_audio([], [])
    assert result == []


def test_build_audio_copy_tracks(sample_audio_tracks):
    """Test the build_audio function with tracks set to copy."""
    # Ensure all tracks are enabled and set to copy
    for track in sample_audio_tracks:
        track.enabled = True
        track.conversion_codec = None

    # Create audio streams
    audio_streams = [Box({"index": 1}), Box({"index": 2}), Box({"index": 3})]

    result = build_audio(sample_audio_tracks, audio_streams)

    # Check that audio tracks are copied
    assert "--audio-copy" in result and "1,2,3" in result


def test_build_audio_convert_tracks(sample_audio_tracks):
    """Test the build_audio function with tracks set to convert."""
    # Set up conversion settings for the tracks
    sample_audio_tracks[0].conversion_codec = "aac"
    sample_audio_tracks[0].conversion_bitrate = "128k"
    sample_audio_tracks[0].downmix = "stereo"

    sample_audio_tracks[1].conversion_codec = "libmp3lame"
    sample_audio_tracks[1].conversion_aq = 3
    sample_audio_tracks[1].downmix = "No Downmix"

    # Create audio streams
    audio_streams = [Box({"index": 1}), Box({"index": 2}), Box({"index": 3})]

    result = build_audio(sample_audio_tracks, audio_streams)

    # Check that audio tracks are converted correctly
    assert "--audio-stream" in result and "1?:stereo" in result
    assert "--audio-codec" in result and "1?aac" in result
    assert "--audio-bitrate" in result and "1?128k" in result
    assert "--audio-codec" in result and "2?libmp3lame" in result
    assert "--audio-quality" in result and "2?3" in result


def test_build_subtitle_empty():
    """Test the build_subtitle function with an empty list."""
    result = build_subtitle([], [], 1080)
    assert result == []


def test_build_subtitle_copy_tracks(sample_subtitle_tracks):
    """Test the build_subtitle function with tracks set to copy."""
    # Ensure all tracks are enabled and not set to burn-in
    for track in sample_subtitle_tracks:
        track.enabled = True
        track.burn_in = False

    # Create subtitle streams
    subtitle_streams = [Box({"index": 0}), Box({"index": 1}), Box({"index": 2})]

    result = build_subtitle(sample_subtitle_tracks, subtitle_streams, 1080)

    # Check that subtitle tracks are copied
    assert "--sub-copy" in result and "1,2,3" in result

    # Check that dispositions are set correctly
    assert "--sub-disposition" in result and "1?default" in result
    assert "2?unset" in result
    assert "3?forced" in result

    # Check that languages are set
    assert "--sub-metadata" in result and "1?language=eng" in result
    assert "2?language=jpn" in result
    assert "3?language=eng" in result


def test_build_subtitle_with_burn_in(sample_subtitle_tracks):
    """Test the build_subtitle function with a burn-in track."""
    # Set one track to burn-in
    sample_subtitle_tracks[0].burn_in = True
    sample_subtitle_tracks[1].burn_in = False
    sample_subtitle_tracks[2].burn_in = False

    # Create subtitle streams
    subtitle_streams = [Box({"index": 0}), Box({"index": 1}), Box({"index": 2})]

    result = build_subtitle(sample_subtitle_tracks, subtitle_streams, 1080)

    # Check that the burn-in track is included with vpp-subburn
    assert "--vpp-subburn" in result and "track=1" in result

    # Check that the other tracks are copied
    assert "--sub-copy" in result and "2,3" in result


def test_build_subtitle_with_external_tracks(sample_subtitle_tracks):
    """Test that build_subtitle generates --sub-source for external subtitle tracks."""
    from fastflix.models.encode import SubtitleTrack

    # Add an external track
    external_track = SubtitleTrack(
        index=0,
        outdex=3,
        language="fre",
        subtitle_type="text",
        enabled=True,
        burn_in=False,
        long_name="[EXT] french.srt",
        external=True,
        file_path="/path/to/french.srt",
        file_index=1,
    )
    tracks_with_external = sample_subtitle_tracks + [external_track]

    subtitle_streams = [Box({"index": 0}), Box({"index": 1}), Box({"index": 2})]

    result = build_subtitle(tracks_with_external, subtitle_streams, 1080)

    # External track should use --sub-source
    assert "--sub-source" in result
    assert "/path/to/french.srt" in result
    # Embedded tracks should still be present
    assert "--sub-copy" in result


def test_build_subtitle_external_only():
    """Test build_subtitle with only external tracks."""
    from fastflix.models.encode import SubtitleTrack

    external_track = SubtitleTrack(
        index=0,
        outdex=0,
        language="eng",
        subtitle_type="text",
        enabled=True,
        burn_in=False,
        long_name="[EXT] english.srt",
        external=True,
        file_path="/path/to/english.srt",
    )

    result = build_subtitle([external_track], [], 1080)

    assert "--sub-source" in result
    assert "/path/to/english.srt" in result
    assert "--sub-copy" not in result


def test_build_subtitle_external_burn_in():
    """Test build_subtitle with external track set to burn-in."""
    from fastflix.models.encode import SubtitleTrack

    external_track = SubtitleTrack(
        index=0,
        outdex=0,
        language="eng",
        subtitle_type="text",
        enabled=True,
        burn_in=True,
        long_name="[EXT] english.srt",
        external=True,
        file_path="/path/to/english.srt",
    )

    result = build_subtitle([external_track], [], 1080)

    assert "--vpp-subburn" in result
    assert "filename=/path/to/english.srt" in result
    assert "--sub-source" not in result


def test_build_subtitle_external_burn_in_4k():
    """Test build_subtitle with external burn-in at 4K resolution includes scale."""
    from fastflix.models.encode import SubtitleTrack

    external_track = SubtitleTrack(
        index=0,
        outdex=0,
        language="eng",
        subtitle_type="text",
        enabled=True,
        burn_in=True,
        long_name="[EXT] english.srt",
        external=True,
        file_path="/path/to/english.srt",
    )

    result = build_subtitle([external_track], [], 2160)

    assert "--vpp-subburn" in result
    assert "filename=/path/to/english.srt,scale=2.0" in result


def test_build_subtitle_external_disabled():
    """Test build_subtitle with disabled external tracks returns empty."""
    from fastflix.models.encode import SubtitleTrack

    external_track = SubtitleTrack(
        index=0,
        outdex=0,
        language="eng",
        subtitle_type="text",
        enabled=False,
        burn_in=False,
        long_name="[EXT] english.srt",
        external=True,
        file_path="/path/to/english.srt",
    )

    result = build_subtitle([external_track], [], 1080)

    assert result == []


def test_build_subtitle_with_4k_scaling(sample_subtitle_tracks):
    """Test the build_subtitle function with 4K scaling."""
    # Set one track to burn-in
    sample_subtitle_tracks[0].burn_in = True

    # Create subtitle streams
    subtitle_streams = [Box({"index": 0}), Box({"index": 1}), Box({"index": 2})]

    result = build_subtitle(sample_subtitle_tracks, subtitle_streams, 2160)

    # Check that the burn-in track includes scale parameter
    assert "--vpp-subburn" in result and "track=1,scale=2.0" in result


# --- _parse_frame_rate tests ---


def test_parse_frame_rate_rational():
    """Test parsing a rational frame rate string like '24000/1001'."""
    result = _parse_frame_rate("24000/1001")
    assert result == pytest.approx(23.976, rel=1e-3)


def test_parse_frame_rate_integer_string():
    """Test parsing a plain integer frame rate string."""
    result = _parse_frame_rate("30")
    assert result == 30.0


def test_parse_frame_rate_float_string():
    """Test parsing a plain float frame rate string."""
    result = _parse_frame_rate("29.97")
    assert result == pytest.approx(29.97)


def test_parse_frame_rate_empty():
    """Test parsing an empty string returns None."""
    assert _parse_frame_rate("") is None


def test_parse_frame_rate_invalid():
    """Test parsing an invalid string returns None."""
    assert _parse_frame_rate("abc") is None


def test_parse_frame_rate_zero_denominator():
    """Test parsing a rational with zero denominator returns None."""
    assert _parse_frame_rate("24000/0") is None


# --- rigaya_trim_or_seek tests ---


def test_rigaya_trim_or_seek_no_times(encc_fastflix_instance):
    """Test that no arguments are returned when no start/end time is set."""
    video = encc_fastflix_instance.current_video
    video.video_settings.start_time = 0
    video.video_settings.end_time = 0
    result = rigaya_trim_or_seek(video)
    assert result == []


def test_rigaya_trim_or_seek_fast_mode(encc_fastflix_instance):
    """Test fast mode (fast_seek=True) uses --seek and --seekto."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = True
    video.video_settings.start_time = 10.5
    video.video_settings.end_time = 120.0
    result = rigaya_trim_or_seek(video)
    assert "--seek" in result
    assert "10.5" in result
    assert "--seekto" in result
    assert "120.0" in result


def test_rigaya_trim_or_seek_fast_mode_start_only(encc_fastflix_instance):
    """Test fast mode with only start_time set."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = True
    video.video_settings.start_time = 5.0
    video.video_settings.end_time = 0
    result = rigaya_trim_or_seek(video)
    assert result == ["--seek", "5.0"]
    assert "--seekto" not in result


def test_rigaya_trim_or_seek_fast_mode_end_only(encc_fastflix_instance):
    """Test fast mode with only end_time set."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = True
    video.video_settings.start_time = 0
    video.video_settings.end_time = 30.0
    result = rigaya_trim_or_seek(video)
    assert "--seek" not in result
    assert result == ["--seekto", "30.0"]


def test_rigaya_trim_or_seek_exact_mode_with_frame_rate(encc_fastflix_instance):
    """Test exact mode (fast_seek=False) with a parseable frame rate uses --trim."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = False
    video.video_settings.start_time = 10.0
    video.video_settings.end_time = 20.0
    # Set a known frame rate on the stream
    video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "bit_depth": 10,
                        "r_frame_rate": "24000/1001",
                        "avg_frame_rate": "24000/1001",
                        "width": 3840,
                        "height": 2160,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    result = rigaya_trim_or_seek(video)
    assert result[0] == "--trim"
    # 10.0 * (24000/1001) ≈ 239.76 → int = 239
    # 20.0 * (24000/1001) ≈ 479.52 → int = 479
    assert result[1] == "239:479"


def test_rigaya_trim_or_seek_exact_mode_start_only(encc_fastflix_instance):
    """Test exact mode with only start_time uses --trim from start_frame to end of video."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = False
    video.video_settings.start_time = 10.0
    video.video_settings.end_time = 0
    video.duration = 60
    video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "bit_depth": 10,
                        "r_frame_rate": "30",
                        "avg_frame_rate": "30",
                        "width": 3840,
                        "height": 2160,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    result = rigaya_trim_or_seek(video)
    assert result == ["--trim", "300:1800"]


def test_rigaya_trim_or_seek_exact_mode_end_only(encc_fastflix_instance):
    """Test exact mode with only end_time uses --trim from frame 0."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = False
    video.video_settings.start_time = 0
    video.video_settings.end_time = 20.0
    video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "bit_depth": 10,
                        "r_frame_rate": "30",
                        "avg_frame_rate": "30",
                        "width": 3840,
                        "height": 2160,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    result = rigaya_trim_or_seek(video)
    assert result == ["--trim", "0:600"]


def test_rigaya_trim_or_seek_exact_mode_no_frame_rate_fallback(encc_fastflix_instance):
    """Test exact mode without frame rate falls back to --seek/--seekto."""
    video = encc_fastflix_instance.current_video
    video.video_settings.fast_seek = False
    video.video_settings.start_time = 10.0
    video.video_settings.end_time = 20.0
    # Stream without r_frame_rate
    video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "bit_depth": 10,
                        "width": 3840,
                        "height": 2160,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    result = rigaya_trim_or_seek(video)
    assert "--seek" in result
    assert "--seekto" in result
    assert "--trim" not in result
