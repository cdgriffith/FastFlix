# -*- coding: utf-8 -*-
from unittest import mock
from box import Box
import pytest

from fastflix.encoders.common.encc_helpers import (
    audio_quality_converter,
    rigaya_avformat_reader,
    rigaya_auto_options,
    rigaya_trim_or_seek,
    rigaya_extra_options,
    RIGAYA_DENOISE_MAP,
    parse_frame_rate,
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


# --- parse_frame_rate tests ---


def testparse_frame_rate_rational():
    """Test parsing a rational frame rate string like '24000/1001'."""
    result = parse_frame_rate("24000/1001")
    assert result == pytest.approx(23.976, rel=1e-3)


def testparse_frame_rate_integer_string():
    """Test parsing a plain integer frame rate string."""
    result = parse_frame_rate("30")
    assert result == 30.0


def testparse_frame_rate_float_string():
    """Test parsing a plain float frame rate string."""
    result = parse_frame_rate("29.97")
    assert result == pytest.approx(29.97)


def testparse_frame_rate_empty():
    """Test parsing an empty string returns None."""
    assert parse_frame_rate("") is None


def testparse_frame_rate_invalid():
    """Test parsing an invalid string returns None."""
    assert parse_frame_rate("abc") is None


def testparse_frame_rate_zero_denominator():
    """Test parsing a rational with zero denominator returns None."""
    assert parse_frame_rate("24000/0") is None


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


# --- rigaya_extra_options tests ---


def test_rigaya_extra_options_equalizer_all(encc_fastflix_instance):
    """Test --vpp-tweak with all four equalizer values set."""
    video = encc_fastflix_instance.current_video
    video.video_settings.brightness = "0.1"
    video.video_settings.contrast = "1.5"
    video.video_settings.saturation = "1.2"
    video.video_settings.gamma = "0.9"
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" in result
    tweak_value = result[result.index("--vpp-tweak") + 1]
    assert "brightness=0.1" in tweak_value
    assert "contrast=1.5" in tweak_value
    assert "saturation=1.2" in tweak_value
    assert "gamma=0.9" in tweak_value


def test_rigaya_extra_options_equalizer_partial(encc_fastflix_instance):
    """Test --vpp-tweak with only some values set."""
    video = encc_fastflix_instance.current_video
    video.video_settings.brightness = "0.2"
    video.video_settings.gamma = "2.0"
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" in result
    tweak_value = result[result.index("--vpp-tweak") + 1]
    assert "brightness=0.2" in tweak_value
    assert "gamma=2.0" in tweak_value
    assert "contrast" not in tweak_value
    assert "saturation" not in tweak_value


def test_rigaya_extra_options_equalizer_defaults_skipped(encc_fastflix_instance):
    """Test that default values produce no --vpp-tweak."""
    video = encc_fastflix_instance.current_video
    video.video_settings.brightness = "0"
    video.video_settings.contrast = "1.0"
    video.video_settings.saturation = "1"
    video.video_settings.gamma = "1.0"
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" not in result


def test_rigaya_extra_options_equalizer_none(encc_fastflix_instance):
    """Test that None values produce no --vpp-tweak."""
    video = encc_fastflix_instance.current_video
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" not in result


def test_rigaya_extra_options_equalizer_clamping(encc_fastflix_instance):
    """Test that values are clamped to rigaya ranges."""
    video = encc_fastflix_instance.current_video
    video.video_settings.brightness = "5.0"  # exceeds 1.0
    video.video_settings.saturation = "-1.0"  # below 0.0
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" in result
    tweak_value = result[result.index("--vpp-tweak") + 1]
    assert "brightness=1.0" in tweak_value
    assert "saturation=0.0" in tweak_value


def test_rigaya_extra_options_denoise_nlmeans(encc_fastflix_instance):
    """Test denoise mapping for nlmeans presets."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "nlmeans=s=1.0:p=3:r=9"
    result = rigaya_extra_options(video)
    assert "--vpp-nlmeans" in result
    assert "sigma=1.0,h=1.0,patch=3,search=9" in result


def test_rigaya_extra_options_denoise_atadenoise(encc_fastflix_instance):
    """Test denoise mapping for atadenoise -> knn."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=9"
    result = rigaya_extra_options(video)
    assert "--vpp-knn" in result


def test_rigaya_extra_options_denoise_hqdn3d(encc_fastflix_instance):
    """Test denoise mapping for hqdn3d -> pmd."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "hqdn3d=luma_spatial=4:chroma_spatial=3:luma_tmp=6:chroma_tmp=4.5"
    result = rigaya_extra_options(video)
    assert "--vpp-pmd" in result


def test_rigaya_extra_options_denoise_vaguedenoiser(encc_fastflix_instance):
    """Test denoise mapping for vaguedenoiser -> pmd."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "vaguedenoiser=threshold=3:method=soft:nsteps=5"
    result = rigaya_extra_options(video)
    assert "--vpp-pmd" in result


def test_rigaya_extra_options_denoise_all_presets_mapped():
    """Test that all 15 known denoise presets have mappings (12 original + 3 nlmeans_opencl)."""
    assert len(RIGAYA_DENOISE_MAP) == 15


def test_rigaya_extra_options_denoise_unknown(encc_fastflix_instance):
    """Test that unknown denoise strings are skipped."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "unknown_filter=strength=5"
    result = rigaya_extra_options(video)
    assert "--vpp-nlmeans" not in result
    assert "--vpp-knn" not in result
    assert "--vpp-pmd" not in result


def test_rigaya_extra_options_deblock_weak(encc_fastflix_instance):
    """Test deblock weak mapping."""
    video = encc_fastflix_instance.current_video
    video.video_settings.deblock = "weak"
    result = rigaya_extra_options(video)
    assert "--vpp-deblock" in result
    assert "strength=30" in result


def test_rigaya_extra_options_deblock_strong(encc_fastflix_instance):
    """Test deblock strong mapping."""
    video = encc_fastflix_instance.current_video
    video.video_settings.deblock = "strong"
    result = rigaya_extra_options(video)
    assert "--vpp-deblock" in result
    assert "strength=60" in result


def test_rigaya_extra_options_output_fps(encc_fastflix_instance):
    """Test output FPS mapping."""
    video = encc_fastflix_instance.current_video
    video.video_settings.output_fps = "24"
    result = rigaya_extra_options(video)
    assert "--vpp-fps" in result
    assert "fps=24" in result


def test_rigaya_extra_options_video_track_title(encc_fastflix_instance):
    """Test video track title mapping."""
    video = encc_fastflix_instance.current_video
    video.video_settings.video_track_title = "My Video"
    result = rigaya_extra_options(video)
    assert "--video-metadata" in result
    assert "title=My Video" in result


def test_rigaya_extra_options_combined(encc_fastflix_instance):
    """Test multiple features combined in a single call."""
    video = encc_fastflix_instance.current_video
    video.video_settings.brightness = "0.1"
    video.video_settings.gamma = "1.5"
    video.video_settings.denoise = "nlmeans=s=10.0:p=13:r=25"
    video.video_settings.deblock = "strong"
    video.video_settings.output_fps = "30"
    video.video_settings.video_track_title = "Test"
    result = rigaya_extra_options(video)
    assert "--vpp-tweak" in result
    assert "--vpp-nlmeans" in result
    assert "--vpp-deblock" in result
    assert "--vpp-fps" in result
    assert "--video-metadata" in result


def test_rigaya_extra_options_sharpen(encc_fastflix_instance):
    """Test that sharpen generates --vpp-unsharp with correct parameters."""
    video = encc_fastflix_instance.current_video
    video.video_settings.sharpen = "0.7"
    result = rigaya_extra_options(video)
    assert "--vpp-unsharp" in result
    idx = result.index("--vpp-unsharp")
    assert "radius=3,weight=0.7" in result[idx + 1]


def test_rigaya_extra_options_sharpen_zero(encc_fastflix_instance):
    """Test that sharpen value of 0 does not add --vpp-unsharp."""
    video = encc_fastflix_instance.current_video
    video.video_settings.sharpen = "0"
    result = rigaya_extra_options(video)
    assert "--vpp-unsharp" not in result


def test_rigaya_extra_options_sharpen_clamped(encc_fastflix_instance):
    """Test that sharpen value is clamped to 1.0 max."""
    video = encc_fastflix_instance.current_video
    video.video_settings.sharpen = "1.5"
    result = rigaya_extra_options(video)
    assert "--vpp-unsharp" in result
    idx = result.index("--vpp-unsharp")
    assert "radius=3,weight=1.0" in result[idx + 1]


def test_rigaya_extra_options_gop_length(encc_fastflix_instance):
    """Test that gop_length generates --gop-len."""
    video = encc_fastflix_instance.current_video
    video.video_settings.gop_length = 250
    result = rigaya_extra_options(video)
    assert "--gop-len" in result
    idx = result.index("--gop-len")
    assert result[idx + 1] == "250"


def test_rigaya_extra_options_gop_length_none(encc_fastflix_instance):
    """Test that no gop_length does not add --gop-len."""
    video = encc_fastflix_instance.current_video
    video.video_settings.gop_length = None
    result = rigaya_extra_options(video)
    assert "--gop-len" not in result


def test_rigaya_extra_options_curves_preset(encc_fastflix_instance):
    """Test that curves_preset generates --vpp-curves."""
    video = encc_fastflix_instance.current_video
    video.video_settings.curves_preset = "vintage"
    result = rigaya_extra_options(video)
    assert "--vpp-curves" in result
    idx = result.index("--vpp-curves")
    assert result[idx + 1] == "preset=vintage"


def test_rigaya_extra_options_curves_preset_none(encc_fastflix_instance):
    """Test that no curves_preset does not add --vpp-curves."""
    video = encc_fastflix_instance.current_video
    video.video_settings.curves_preset = None
    result = rigaya_extra_options(video)
    assert "--vpp-curves" not in result


def test_rigaya_extra_options_lut3d(encc_fastflix_instance):
    """Test that lut3d_path generates --vpp-colorspace with lut3d."""
    video = encc_fastflix_instance.current_video
    video.video_settings.lut3d_path = "/path/to/my.cube"
    result = rigaya_extra_options(video)
    assert "--vpp-colorspace" in result
    idx = result.index("--vpp-colorspace")
    assert "lut3d=/path/to/my.cube" in result[idx + 1]
    assert "lut3d_interp=tetrahedral" in result[idx + 1]


def test_rigaya_extra_options_lut3d_none(encc_fastflix_instance):
    """Test that no lut3d_path does not add --vpp-colorspace."""
    video = encc_fastflix_instance.current_video
    video.video_settings.lut3d_path = None
    result = rigaya_extra_options(video)
    assert "--vpp-colorspace" not in result


def test_rigaya_extra_options_unsharp_preset(encc_fastflix_instance):
    """Test that unsharp preset generates --vpp-unsharp with correct parameters."""
    video = encc_fastflix_instance.current_video
    video.video_settings.unsharp = "unsharp=5:5:1.0:5:5:0.5"
    result = rigaya_extra_options(video)
    assert "--vpp-unsharp" in result
    idx = result.index("--vpp-unsharp")
    assert "radius=3,weight=0.6" in result[idx + 1]


def test_rigaya_extra_options_unsharp_overrides_sharpen(encc_fastflix_instance):
    """Test that when both unsharp and sharpen are set, unsharp takes priority."""
    video = encc_fastflix_instance.current_video
    video.video_settings.unsharp = "unsharp=5:5:0.5:5:5:0.0"
    video.video_settings.sharpen = "0.8"
    result = rigaya_extra_options(video)
    # Should only have one --vpp-unsharp (from unsharp, not sharpen)
    count = result.count("--vpp-unsharp")
    assert count == 1
    idx = result.index("--vpp-unsharp")
    assert "radius=3,weight=0.3" in result[idx + 1]


def test_rigaya_extra_options_pad_16_9(encc_fastflix_instance):
    """Test that pad aspect 16:9 generates --vpp-pad for 4:3 source."""
    video = encc_fastflix_instance.current_video
    # Set up a 4:3 source (1440x1080) via streams
    video.streams.video[0].width = 1440
    video.streams.video[0].height = 1080
    video.video_settings.pad_aspect = "16:9"
    result = rigaya_extra_options(video)
    assert "--vpp-pad" in result
    idx = result.index("--vpp-pad")
    # 1080 * 16/9 = 1920, pad_left = (1920-1440)/2 = 240
    assert "240,0,240,0" in result[idx + 1]


def test_rigaya_extra_options_pad_none(encc_fastflix_instance):
    """Test that no pad_aspect does not add --vpp-pad."""
    video = encc_fastflix_instance.current_video
    video.video_settings.pad_aspect = None
    result = rigaya_extra_options(video)
    assert "--vpp-pad" not in result


def test_rigaya_extra_options_nlmeans_opencl(encc_fastflix_instance):
    """Test that nlmeans_opencl denoise maps to rigaya --vpp-nlmeans."""
    video = encc_fastflix_instance.current_video
    video.video_settings.denoise = "nlmeans_opencl=s=1.0:p=3:r=9"
    result = rigaya_extra_options(video)
    assert "--vpp-nlmeans" in result
    idx = result.index("--vpp-nlmeans")
    assert "sigma=1.0,h=1.0,patch=3,search=9" in result[idx + 1]
