# -*- coding: utf-8 -*-

from fastflix.encoders.common.audio import audio_quality_converter, build_audio, channel_list, lossless


def test_channel_list():
    """Test the channel_list dictionary."""
    # Verify some key entries in the channel_list
    assert channel_list["mono"] == 1
    assert channel_list["stereo"] == 2
    assert channel_list["5.1"] == 6
    assert channel_list["7.1"] == 8


def test_lossless_codecs():
    """Test the lossless codecs list."""
    # Verify the lossless codecs list
    assert "flac" in lossless
    assert "truehd" in lossless
    assert "alac" in lossless
    assert "aac" not in lossless
    assert "ac3" not in lossless


def test_audio_quality_converter_libopus():
    """Test the audio_quality_converter function with libopus codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libopus", channels=2, track_number=1)
    assert result == "-vbr:1 on -b:1 240k"

    result = audio_quality_converter(5, "libopus", channels=2, track_number=1)
    assert result == "-vbr:1 on -b:1 48k"

    # Test with different channel counts
    result = audio_quality_converter(0, "libopus", channels=6, track_number=1)
    assert result == "-vbr:1 on -b:1 720k"


def test_audio_quality_converter_aac():
    """Test the audio_quality_converter function with aac codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "aac", channels=2, track_number=1)
    assert result == "-q:1 2"

    result = audio_quality_converter(5, "aac", channels=2, track_number=1)
    assert result == "-q:1 1"

    result = audio_quality_converter(9, "aac", channels=2, track_number=1)
    assert result == "-q:1 0.2"


def test_audio_quality_converter_libfdk_aac():
    """Test the audio_quality_converter function with libfdk_aac codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libfdk_aac", channels=2, track_number=1)
    assert result == "-q:1 1"

    result = audio_quality_converter(5, "libfdk_aac", channels=2, track_number=1)
    assert result == "-q:1 3"

    result = audio_quality_converter(9, "libfdk_aac", channels=2, track_number=1)
    assert result == "-q:1 5"


def test_audio_quality_converter_libvorbis():
    """Test the audio_quality_converter function with libvorbis codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libvorbis", channels=2, track_number=1)
    assert result == "-q:1 10"

    result = audio_quality_converter(5, "libvorbis", channels=2, track_number=1)
    assert result == "-q:1 5"

    result = audio_quality_converter(9, "libvorbis", channels=2, track_number=1)
    assert result == "-q:1 1"

    # Test with vorbis alias
    result = audio_quality_converter(0, "vorbis", channels=2, track_number=1)
    assert result == "-q:1 10"


def test_audio_quality_converter_mp3():
    """Test the audio_quality_converter function with mp3 codec."""
    # Test with different quality levels
    result = audio_quality_converter(0, "libmp3lame", channels=2, track_number=1)
    assert result == "-q:1 0"

    result = audio_quality_converter(5, "libmp3lame", channels=2, track_number=1)
    assert result == "-q:1 5"

    # Test with mp3 alias
    result = audio_quality_converter(0, "mp3", channels=2, track_number=1)
    assert result == "-q:1 0"


def test_audio_quality_converter_ac3():
    """Test the audio_quality_converter function with ac3 codec."""
    # Test with different quality levels and channel counts
    result = audio_quality_converter(0, "ac3", channels=2, track_number=1)
    assert result == "-b:1 960k"

    result = audio_quality_converter(5, "ac3", channels=6, track_number=1)
    assert result == "-b:1 576k"

    # Test with eac3
    result = audio_quality_converter(0, "eac3", channels=2, track_number=1)
    assert result == "-b:1 960k"

    # Test with truehd
    result = audio_quality_converter(0, "truehd", channels=2, track_number=1)
    assert result == "-b:1 960k"


def test_audio_quality_converter_default():
    """Test the audio_quality_converter function with default fallback."""
    # Test with an unknown codec
    result = audio_quality_converter(0, "unknown_codec", channels=2, track_number=1)
    assert result == "-b:1 240k"

    result = audio_quality_converter(5, "unknown_codec", channels=6, track_number=1)
    assert result == "-b:1 144k"


def test_build_audio_empty():
    """Test the build_audio function with an empty list."""
    result = build_audio([])
    assert result == ""


def test_build_audio_disabled_tracks(sample_audio_tracks):
    """Test the build_audio function with disabled tracks."""
    # Make all tracks disabled
    for track in sample_audio_tracks:
        track.enabled = False

    result = build_audio(sample_audio_tracks)
    assert result == ""


def test_build_audio_copy_tracks(sample_audio_tracks):
    """Test the build_audio function with tracks set to copy."""
    # Ensure all tracks are enabled and set to copy
    for track in sample_audio_tracks:
        track.enabled = True
        track.conversion_codec = None

    result = build_audio(sample_audio_tracks)

    # Check that each track is mapped and copied
    assert "-map 0:1" in result
    assert "-map 0:2" in result
    assert "-map 0:3" in result
    assert "-c:0 copy" in result
    assert "-c:1 copy" in result
    assert "-c:2 copy" in result

    # Check that titles and languages are set
    assert 'title="Surround 5.1"' in result
    assert 'title="Stereo"' in result
    assert "language=eng" in result
    assert "language=jpn" in result


def test_build_audio_convert_tracks(sample_audio_tracks):
    """Test the build_audio function with tracks set to convert."""
    # Set up conversion settings for the tracks
    sample_audio_tracks[0].conversion_codec = "aac"
    sample_audio_tracks[0].conversion_bitrate = "128k"
    sample_audio_tracks[0].downmix = "stereo"

    sample_audio_tracks[1].conversion_codec = "libmp3lame"
    sample_audio_tracks[1].conversion_aq = 3
    sample_audio_tracks[1].downmix = "No Downmix"

    result = build_audio(sample_audio_tracks)

    # Check that each track is mapped and converted correctly
    assert "-map 0:1" in result
    assert "-map 0:2" in result
    assert "-c:0 aac -b:0 128k -ac:0 2" in result
    assert "-c:1 libmp3lame -q:1 3" in result
    assert "aformat=channel_layouts=stereo" in result
    assert "aformat=channel_layouts=stereo" in result

    # Check that titles and languages are set
    assert 'title="Surround 5.1"' in result
    assert 'title="Stereo"' in result
    assert "language=eng" in result
    assert "language=jpn" in result


def test_build_audio_with_dispositions(sample_audio_tracks):
    """Test the build_audio function with dispositions."""
    # Set up dispositions for the tracks
    sample_audio_tracks[0].dispositions = {"default": True, "forced": False}
    sample_audio_tracks[1].dispositions = {"default": False, "forced": True}
    sample_audio_tracks[2].dispositions = {}
    sample_audio_tracks[2].enabled = True

    result = build_audio(sample_audio_tracks)

    # Check that dispositions are set correctly
    assert "-disposition:0 default" in result
    assert "-disposition:1 forced" in result
    assert "-disposition:2" not in result


def test_build_audio_with_strict_codecs(sample_audio_tracks):
    """Test the build_audio function with codecs that require -strict -2."""
    # Set up tracks with codecs that require -strict -2
    sample_audio_tracks[0].conversion_codec = "truehd"
    sample_audio_tracks[1].conversion_codec = "opus"
    sample_audio_tracks[2].conversion_codec = "dca"

    result = build_audio(sample_audio_tracks)

    # Check that -strict -2 is added
    assert "-strict -2" in result
