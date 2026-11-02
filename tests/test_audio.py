# -*- coding: utf-8 -*-

from box import Box

from .general import test_audio_tracks

from fastflix.audio_processing import apply_audio_filters
from fastflix.models.profiles import AudioMatch, MatchType, MatchItem
from fastflix.models.encode import AudioTrack
from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.encc_helpers import audio_quality_converter as encc_audio_quality_converter


def test_audio_filters():
    test_filters = [
        AudioMatch(
            match_type=MatchType.FIRST,
            match_item=MatchItem.TITLE,
            match_input="Surround 5",
            conversion=None,
            bitrate="32k",
            downmix="No Downmix",
        ),
        AudioMatch(
            match_type=MatchType.LAST,
            match_item=MatchItem.ALL,
            match_input="*",
            conversion=None,
            bitrate="32k",
            downmix="No Downmix",
        ),
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.LANGUAGE,
            match_input="eng",
            conversion=None,
            bitrate="32k",
            downmix="No Downmix",
        ),
    ]

    result = apply_audio_filters(audio_filters=test_filters, original_tracks=test_audio_tracks)

    # Results are sorted by index; verify track indices and their matched filters
    result_indices = [track.index for track, _ in result]

    # FIRST title "Surround 5" -> index 1 (truehd)
    # LAST ALL -> index 6 (last track, dts)
    # ALL language eng -> indices 1, 2, 5, 6
    # Sorted by index (stable sort preserves insertion order for same index)
    assert result_indices == [1, 1, 2, 5, 6, 6]

    # First result: truehd track matched by TITLE
    assert result[0][0].codec_name == "truehd"
    assert result[0][1].match_item == MatchItem.TITLE

    # Second result: truehd track matched by LANGUAGE eng
    assert result[1][0].codec_name == "truehd"
    assert result[1][1].match_item == MatchItem.LANGUAGE

    # Third result: ac3 track matched by LANGUAGE eng
    assert result[2][0].codec_name == "ac3"
    assert result[2][0].index == 2
    assert result[2][1].match_item == MatchItem.LANGUAGE

    # Fourth result: dts DTS-HD MA track matched by LANGUAGE eng
    assert result[3][0].codec_name == "dts"
    assert result[3][0].index == 5
    assert result[3][1].match_item == MatchItem.LANGUAGE

    # Fifth result: dts track matched by LAST ALL (inserted before LANGUAGE for same index)
    assert result[4][0].index == 6
    assert result[4][1].match_item == MatchItem.ALL

    # Sixth result: dts track matched by LANGUAGE eng
    assert result[5][0].codec_name == "dts"
    assert result[5][0].index == 6
    assert result[5][1].match_item == MatchItem.LANGUAGE


def test_audio_filters_codec_match():
    """Test matching audio tracks by codec name."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC,
            match_input="truehd",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 2
    assert result[0][0].codec_name == "truehd"
    assert result[0][0].index == 1
    assert result[1][0].codec_name == "truehd"
    assert result[1][0].index == 3


def test_audio_filters_codec_match_first():
    """Test matching first audio track by codec name."""
    filters = [
        AudioMatch(
            match_type=MatchType.FIRST,
            match_item=MatchItem.CODEC,
            match_input="ac3",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].codec_name == "ac3"
    assert result[0][0].index == 2


def test_audio_filters_codec_match_last():
    """Test matching last audio track by codec name."""
    filters = [
        AudioMatch(
            match_type=MatchType.LAST,
            match_item=MatchItem.CODEC,
            match_input="ac3",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].codec_name == "ac3"
    assert result[0][0].index == 4


def test_audio_filters_codec_match_all_dts():
    """Test matching all DTS tracks by codec name."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC,
            match_input="dts",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 2
    assert result[0][0].codec_name == "dts"
    assert result[1][0].codec_name == "dts"


def test_audio_filters_codec_match_case_insensitive():
    """Test that codec matching is case insensitive."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC,
            match_input="TrueHD",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 2
    assert all(track.codec_name == "truehd" for track, _ in result)


def test_audio_filters_codec_profile_match():
    """Test matching audio tracks by codec and profile (e.g. DTS-HD MA vs DTS)."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC_PROFILE,
            match_input="dts:DTS-HD MA",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].codec_name == "dts"
    assert result[0][0].profile == "DTS-HD MA"
    assert result[0][0].index == 5


def test_audio_filters_codec_profile_match_regular_dts():
    """Test matching regular DTS (not DTS-HD MA) by codec and profile."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC_PROFILE,
            match_input="dts:DTS",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].codec_name == "dts"
    assert result[0][0].profile == "DTS"
    assert result[0][0].index == 6


def test_audio_filters_codec_profile_case_insensitive():
    """Test that codec:profile matching is case insensitive."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC_PROFILE,
            match_input="DTS:dts-hd ma",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].profile == "DTS-HD MA"


def test_audio_filters_codec_profile_no_match():
    """Test codec:profile matching returns empty when no match."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC_PROFILE,
            match_input="dts:DTS-HD HRA",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 0


def test_audio_filters_codec_profile_truehd_atmos():
    """Test matching TrueHD+Atmos profile."""
    filters = [
        AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.CODEC_PROFILE,
            match_input="truehd:TrueHD+Atmos",
        ),
    ]
    result = apply_audio_filters(audio_filters=filters, original_tracks=test_audio_tracks)
    assert len(result) == 1
    assert result[0][0].codec_name == "truehd"
    assert result[0][0].profile == "TrueHD+Atmos"


class TestAudioMatchValidator:
    """Tests for AudioMatch validator returning correct enum type."""

    def test_match_item_validator_returns_match_item_from_list(self):
        """Test that match_item_must_be_enum validator returns MatchItem, not MatchType."""
        # When loaded from YAML, match_item may come as a list [int_value]
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=[2],  # Simulates YAML loading - should become MatchItem.TITLE
            match_input="*",
        )
        assert isinstance(audio_match.match_item, MatchItem)
        assert audio_match.match_item == MatchItem.TITLE

    def test_match_item_validator_returns_match_item_from_int(self):
        """Test that match_item_must_be_enum validator returns MatchItem from int."""
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=3,  # Should become MatchItem.TRACK
            match_input="*",
        )
        assert isinstance(audio_match.match_item, MatchItem)
        assert audio_match.match_item == MatchItem.TRACK

    def test_match_item_validator_with_all_enum_values(self):
        """Test validator with all MatchItem enum values."""
        for item in MatchItem:
            audio_match = AudioMatch(
                match_type=MatchType.ALL,
                match_item=[item.value],
                match_input="*",
            )
            assert audio_match.match_item == item


class TestDownmixMapping:
    """Tests for downmix string mapping."""

    def test_downmix_mono_is_correct(self):
        """Test that mono downmix produces 'mono', not 'monoo'."""
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.ALL,
            match_input="*",
            downmix=1,  # Should become "mono"
        )
        assert audio_match.downmix == "mono"

    def test_downmix_stereo_mapping(self):
        """Test that stereo downmix maps correctly."""
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.ALL,
            match_input="*",
            downmix=2,
        )
        assert audio_match.downmix == "stereo"

    def test_downmix_51_mapping(self):
        """Test that 5.1 downmix maps correctly."""
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.ALL,
            match_input="*",
            downmix=6,
        )
        assert audio_match.downmix == "5.1"

    def test_downmix_string_passthrough(self):
        """Test that string downmix values pass through unchanged."""
        audio_match = AudioMatch(
            match_type=MatchType.ALL,
            match_item=MatchItem.ALL,
            match_input="*",
            downmix="stereo",
        )
        assert audio_match.downmix == "stereo"


class TestEnccAudioQualityConverter:
    """Tests for encc_helpers audio_quality_converter handling None."""

    def test_audio_quality_converter_handles_zero(self):
        """Test that audio_quality_converter handles quality=0 correctly."""
        result = encc_audio_quality_converter(0, "libopus", channels=2, track_number=1)
        assert "240k" in result

    def test_audio_quality_converter_handles_valid_quality(self):
        """Test that audio_quality_converter handles valid quality values."""
        result = encc_audio_quality_converter(5, "aac", channels=2, track_number=1)
        assert "audio-quality" in result or "audio-bitrate" in result


class TestBuildAudioAttributeError:
    """Tests for build_audio handling AttributeError when raw_info is None."""

    def test_build_audio_with_none_raw_info(self):
        """Test that build_audio handles None raw_info gracefully."""
        track = AudioTrack(
            index=1,
            outdex=0,
            codec="aac",
            title="Test",
            language="eng",
            channels=2,
            enabled=True,
            raw_info=None,  # This should not cause AttributeError
            conversion_codec="aac",
            conversion_bitrate="128k",
            downmix="stereo",
            dispositions={"default": False},
        )
        # Should not raise AttributeError
        result = build_audio([track])
        assert "-c:0" in result and "aac" in result

    def test_build_audio_with_raw_info_missing_channel_layout(self):
        """Test that build_audio handles raw_info without channel_layout."""
        track = AudioTrack(
            index=1,
            outdex=0,
            codec="aac",
            title="Test",
            language="eng",
            channels=2,
            enabled=True,
            raw_info=Box({"channels": 2}),  # Missing channel_layout
            conversion_codec="aac",
            conversion_bitrate="128k",
            downmix=None,  # Will try to access raw_info.channel_layout
            dispositions={"default": False},
        )
        # Should fall back to stereo without crashing
        result = build_audio([track])
        assert "-c:0" in result and "aac" in result
