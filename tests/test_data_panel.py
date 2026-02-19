# -*- coding: utf-8 -*-
from pathlib import Path

from box import Box

from fastflix.models.encode import DataTrack
from fastflix.encoders.common.encc_helpers import build_data
from fastflix.encoders.common.helpers import generate_ending


class TestDataTrackModel:
    def test_create_data_track(self):
        track = DataTrack(index=5, outdex=3, codec_name="bin_data", codec_type="data")
        assert track.index == 5
        assert track.outdex == 3
        assert track.enabled is True
        assert track.codec_name == "bin_data"
        assert track.codec_type == "data"

    def test_create_attachment_track(self):
        track = DataTrack(
            index=10,
            outdex=5,
            codec_name="ttf",
            codec_type="attachment",
            mimetype="application/x-truetype-font",
            filename="Arial.ttf",
        )
        assert track.codec_type == "attachment"
        assert track.mimetype == "application/x-truetype-font"
        assert track.filename == "Arial.ttf"

    def test_defaults(self):
        track = DataTrack(index=0, outdex=0)
        assert track.enabled is True
        assert track.codec_name == ""
        assert track.codec_type == ""
        assert track.title == ""
        assert track.mimetype == ""
        assert track.filename == ""
        assert track.friendly_info == ""
        assert track.raw_info is None

    def test_serialization(self):
        track = DataTrack(index=5, outdex=3, codec_name="tmcd", codec_type="data", title="Timecode")
        data = track.model_dump()
        assert data["index"] == 5
        assert data["codec_name"] == "tmcd"
        restored = DataTrack(**data)
        assert restored.index == track.index
        assert restored.codec_name == track.codec_name


class TestBuildDataRigaya:
    def test_empty_tracks(self):
        result = build_data([], [], [])
        assert result == []

    def test_data_only(self):
        tracks = [DataTrack(index=5, outdex=3, enabled=True, codec_type="data")]
        data_streams = [Box({"index": 5})]
        result = build_data(tracks, data_streams, [])
        assert "--data-copy" in result
        assert "1" in result

    def test_attachment_only(self):
        tracks = [DataTrack(index=10, outdex=5, enabled=True, codec_type="attachment")]
        attachment_streams = [Box({"index": 10})]
        result = build_data(tracks, [], attachment_streams)
        assert "--attachment-copy" in result
        assert "1" in result

    def test_mixed_data_and_attachment(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=True, codec_type="data"),
            DataTrack(index=10, outdex=4, enabled=True, codec_type="attachment"),
        ]
        data_streams = [Box({"index": 5})]
        attachment_streams = [Box({"index": 10})]
        result = build_data(tracks, data_streams, attachment_streams)
        assert "--data-copy" in result
        assert "--attachment-copy" in result

    def test_disabled_tracks(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=False, codec_type="data"),
            DataTrack(index=10, outdex=4, enabled=False, codec_type="attachment"),
        ]
        data_streams = [Box({"index": 5})]
        attachment_streams = [Box({"index": 10})]
        result = build_data(tracks, data_streams, attachment_streams)
        assert result == []

    def test_partial_disabled(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=True, codec_type="data"),
            DataTrack(index=10, outdex=4, enabled=False, codec_type="attachment"),
        ]
        data_streams = [Box({"index": 5})]
        attachment_streams = [Box({"index": 10})]
        result = build_data(tracks, data_streams, attachment_streams)
        assert "--data-copy" in result
        assert "--attachment-copy" not in result

    def test_multiple_data_streams(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=True, codec_type="data"),
            DataTrack(index=6, outdex=4, enabled=True, codec_type="data"),
        ]
        data_streams = [Box({"index": 5}), Box({"index": 6})]
        result = build_data(tracks, data_streams, [])
        assert "--data-copy" in result
        idx = result.index("--data-copy")
        assert result[idx + 1] == "1,2"


class TestGenerateEndingWithDataTracks:
    def test_with_data_tracks(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=True, codec_type="data"),
            DataTrack(index=10, outdex=4, enabled=True, codec_type="attachment"),
        ]
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
            data_tracks=tracks,
        )
        assert "-map" in result
        assert "0:5" in result
        assert "0:10" in result
        assert "-c:d" in result
        assert "copy" in result
        assert "-c:t" in result

    def test_with_disabled_data_tracks(self):
        tracks = [
            DataTrack(index=5, outdex=3, enabled=False, codec_type="data"),
        ]
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
            data_tracks=tracks,
        )
        assert "0:5" not in result
        assert "-c:d" not in result

    def test_data_tracks_override_copy_data(self):
        """When data_tracks is provided, copy_data should be ignored."""
        tracks = [DataTrack(index=5, outdex=3, enabled=True, codec_type="data")]
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
            data_tracks=tracks,
            copy_data=True,
        )
        # Should use per-track mapping, not bulk copy
        assert "0:5" in result
        assert "0:d" not in result

    def test_fallback_copy_data(self):
        """When no data_tracks, copy_data=True should still work."""
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
            copy_data=True,
        )
        assert "0:d" in result
        assert "-c:d" in result

    def test_no_data(self):
        """When no data_tracks and copy_data=False, no data mapping."""
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
        )
        assert "-c:d" not in result
        assert "0:d" not in result

    def test_attachment_only_codec(self):
        """When only attachment tracks, should set -c:t copy but not -c:d."""
        tracks = [DataTrack(index=10, outdex=4, enabled=True, codec_type="attachment")]
        result, _ = generate_ending(
            audio=[],
            subtitles=[],
            output_video=Path("output.mkv"),
            data_tracks=tracks,
        )
        assert "-c:t" in result
        assert "-c:d" not in result
