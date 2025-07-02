# -*- coding: utf-8 -*-

from fastflix.encoders.common.subtitles import build_subtitle
from fastflix.models.encode import SubtitleTrack


def test_build_subtitle_empty():
    """Test the build_subtitle function with an empty list."""
    result, burn_in_track, burn_in_type = build_subtitle([])
    assert result == "-default_mode infer_no_subs"
    assert burn_in_track is None
    assert burn_in_type is None


def test_build_subtitle_disabled_tracks(sample_subtitle_tracks):
    """Test the build_subtitle function with disabled tracks."""
    # Make all tracks disabled
    for track in sample_subtitle_tracks:
        track.enabled = False

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)
    assert result == "-default_mode infer_no_subs"
    assert burn_in_track is None
    assert burn_in_type is None


def test_build_subtitle_copy_tracks(sample_subtitle_tracks):
    """Test the build_subtitle function with tracks set to copy (no burn-in)."""
    # Ensure all tracks are enabled and not set to burn-in
    for track in sample_subtitle_tracks:
        track.enabled = True
        track.burn_in = False

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)

    # Check that each track is mapped and copied
    assert "-map 0:0 -c:0 copy" in result
    assert "-map 0:1 -c:1 copy" in result
    assert "-map 0:2 -c:2 copy" in result

    # Check that languages are set
    assert "language='eng'" in result
    assert "language='jpn'" in result

    # Check that dispositions are set correctly
    assert "-disposition:0 default" in result
    assert "-disposition:1 0" in result
    assert "-disposition:2 forced" in result

    # Check that burn-in track and type are None
    assert burn_in_track is None
    assert burn_in_type is None


def test_build_subtitle_with_burn_in(sample_subtitle_tracks):
    """Test the build_subtitle function with a burn-in track."""
    # Set one track to burn-in
    sample_subtitle_tracks[0].burn_in = True
    sample_subtitle_tracks[1].burn_in = False
    sample_subtitle_tracks[2].burn_in = False

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)

    # Check that the burn-in track is not included in the command
    assert "-map 0:0" not in result

    # Check that the other tracks are mapped and copied with adjusted outdex
    assert "-map 0:1 -c:1 copy" in result
    assert "-map 0:2 -c:2 copy" in result

    # Check that languages are set
    assert "language='jpn'" in result
    assert "language='eng'" in result

    # Check that dispositions are set correctly
    assert "-disposition:1 0" in result
    assert "-disposition:2 forced" in result

    # Check that burn-in track and type are set correctly
    assert burn_in_track == 0
    assert burn_in_type == "text"


def test_build_subtitle_with_different_subtitle_types(sample_subtitle_tracks):
    """Test the build_subtitle function with different subtitle types."""
    # Set different subtitle types
    sample_subtitle_tracks[0].subtitle_type = "text"
    sample_subtitle_tracks[1].subtitle_type = "picture"
    sample_subtitle_tracks[2].subtitle_type = "text"

    # Set one track to burn-in
    sample_subtitle_tracks[0].burn_in = False
    sample_subtitle_tracks[1].burn_in = True
    sample_subtitle_tracks[2].burn_in = False

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)

    # Check that the burn-in track is not included in the command
    assert "-map 0:1" not in result

    # Check that the other tracks are mapped and copied
    assert "-map 0:0 -c:0 copy" in result
    assert "-map 0:2 -c:1 copy" in result

    # Check that burn-in track and type are set correctly
    assert burn_in_track == 1
    assert burn_in_type == "picture"


def test_build_subtitle_with_default_subs_enabled(sample_subtitle_tracks):
    """Test the build_subtitle function with default subtitles enabled."""
    # Set default disposition on one track
    sample_subtitle_tracks[0].dispositions = {"default": True, "forced": False}
    sample_subtitle_tracks[1].dispositions = {"default": False, "forced": False}
    sample_subtitle_tracks[2].dispositions = {"default": False, "forced": False}

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)

    # Check that default_mode is not added since there's a default track
    assert "-default_mode infer_no_subs" not in result


def test_build_subtitle_with_no_default_or_forced_subs(sample_subtitle_tracks):
    """Test the build_subtitle function with no default or forced subtitles."""
    # Set no default or forced dispositions
    sample_subtitle_tracks[0].dispositions = {"default": False, "forced": False}
    sample_subtitle_tracks[1].dispositions = {"default": False, "forced": False}
    sample_subtitle_tracks[2].dispositions = {"default": False, "forced": False}

    result, burn_in_track, burn_in_type = build_subtitle(sample_subtitle_tracks)

    # Check that default_mode is added
    assert "-default_mode infer_no_subs" in result


def test_build_subtitle_with_custom_file_index():
    """Test the build_subtitle function with a custom subtitle file index."""
    # Create a simple subtitle track
    subtitle_track = SubtitleTrack(
        index=0,
        outdex=0,
        language="eng",
        subtitle_type="text",
        enabled=True,
        burn_in=False,
        long_name="English",
        dispositions={"default": True, "forced": False},
    )

    result, burn_in_track, burn_in_type = build_subtitle([subtitle_track], subtitle_file_index=1)

    # Check that the custom file index is used
    assert "-map 1:0" in result
