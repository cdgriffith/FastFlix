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

    expected_result = [
        (
            Box(
                {
                    "avg_frame_rate": "0/0",
                    "bits_per_raw_sample": "24",
                    "bits_per_sample": 0,
                    "channel_layout": "5.1(side)",
                    "channels": 6,
                    "codec_long_name": "TrueHD",
                    "codec_name": "truehd",
                    "codec_tag": "0x0000",
                    "codec_tag_string": "[0][0][0][0]",
                    "codec_type": "audio",
                    "disposition": {
                        "attached_pic": 0,
                        "captions": 0,
                        "clean_effects": 0,
                        "comment": 0,
                        "default": 0,
                        "dependent": 0,
                        "descriptions": 0,
                        "dub": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "karaoke": 0,
                        "lyrics": 0,
                        "metadata": 0,
                        "original": 0,
                        "still_image": 0,
                        "timed_thumbnails": 0,
                        "visual_impaired": 0,
                    },
                    "index": 1,
                    "r_frame_rate": "0/0",
                    "sample_fmt": "s32",
                    "sample_rate": "48000",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "tags": {
                        "BPS-eng": "1921846",
                        "DURATION-eng": "00:23:38.083333333",
                        "NUMBER_OF_BYTES-eng": "340667312",
                        "NUMBER_OF_FRAMES-eng": "1701700",
                        "SOURCE_ID-eng": "001100",
                        "_STATISTICS_TAGS-eng": "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID",
                        "_STATISTICS_WRITING_DATE_UTC-eng": "2021-04-21 20:00:45",
                        "language": "eng",
                        "title": "Surround 5.1",
                    },
                    "time_base": "1/1000",
                }
            ),
            AudioMatch(
                match_type=MatchType.FIRST,
                match_item=MatchItem.TITLE,
                match_input="Surround 5",
                conversion=None,
                bitrate="32k",
                downmix="No Downmix",
            ),
        ),
        (
            Box(
                {
                    "avg_frame_rate": "0/0",
                    "bits_per_raw_sample": "24",
                    "bits_per_sample": 0,
                    "channel_layout": "5.1(side)",
                    "channels": 6,
                    "codec_long_name": "TrueHD",
                    "codec_name": "truehd",
                    "codec_tag": "0x0000",
                    "codec_tag_string": "[0][0][0][0]",
                    "codec_type": "audio",
                    "disposition": {
                        "attached_pic": 0,
                        "captions": 0,
                        "clean_effects": 0,
                        "comment": 0,
                        "default": 0,
                        "dependent": 0,
                        "descriptions": 0,
                        "dub": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "karaoke": 0,
                        "lyrics": 0,
                        "metadata": 0,
                        "original": 0,
                        "still_image": 0,
                        "timed_thumbnails": 0,
                        "visual_impaired": 0,
                    },
                    "index": 1,
                    "r_frame_rate": "0/0",
                    "sample_fmt": "s32",
                    "sample_rate": "48000",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "tags": {
                        "BPS-eng": "1921846",
                        "DURATION-eng": "00:23:38.083333333",
                        "NUMBER_OF_BYTES-eng": "340667312",
                        "NUMBER_OF_FRAMES-eng": "1701700",
                        "SOURCE_ID-eng": "001100",
                        "_STATISTICS_TAGS-eng": "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID",
                        "_STATISTICS_WRITING_DATE_UTC-eng": "2021-04-21 20:00:45",
                        "language": "eng",
                        "title": "Surround 5.1",
                    },
                    "time_base": "1/1000",
                }
            ),
            AudioMatch(
                match_type=MatchType.ALL,
                match_item=MatchItem.LANGUAGE,
                match_input="eng",
                conversion=None,
                bitrate="32k",
                downmix="No Downmix",
            ),
        ),
        (
            Box(
                {
                    "avg_frame_rate": "0/0",
                    "bit_rate": "448000",
                    "bits_per_sample": 0,
                    "channel_layout": "5.1(side)",
                    "channels": 6,
                    "codec_long_name": "ATSC A/52A (AC-3)",
                    "codec_name": "ac3",
                    "codec_tag": "0x0000",
                    "codec_tag_string": "[0][0][0][0]",
                    "codec_type": "audio",
                    "disposition": {
                        "attached_pic": 0,
                        "captions": 0,
                        "clean_effects": 0,
                        "comment": 0,
                        "default": 0,
                        "dependent": 0,
                        "descriptions": 0,
                        "dub": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "karaoke": 0,
                        "lyrics": 0,
                        "metadata": 0,
                        "original": 0,
                        "still_image": 0,
                        "timed_thumbnails": 0,
                        "visual_impaired": 0,
                    },
                    "index": 2,
                    "r_frame_rate": "0/0",
                    "sample_fmt": "fltp",
                    "sample_rate": "48000",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "tags": {
                        "BPS-eng": "448000",
                        "DURATION-eng": "00:23:38.112000000",
                        "NUMBER_OF_BYTES-eng": "79414272",
                        "NUMBER_OF_FRAMES-eng": "44316",
                        "SOURCE_ID-eng": "001100",
                        "_STATISTICS_TAGS-eng": "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID",
                        "_STATISTICS_WRITING_DATE_UTC-eng": "2021-04-21 20:00:45",
                        "language": "eng",
                        "title": "Surround 5.1",
                    },
                    "time_base": "1/1000",
                }
            ),
            AudioMatch(
                match_type=MatchType.ALL,
                match_item=MatchItem.LANGUAGE,
                match_input="eng",
                conversion=None,
                bitrate="32k",
                downmix="No Downmix",
            ),
        ),
        (
            Box(
                {
                    "avg_frame_rate": "0/0",
                    "bit_rate": "192000",
                    "bits_per_sample": 0,
                    "channel_layout": "stereo",
                    "channels": 2,
                    "codec_long_name": "ATSC A/52A (AC-3)",
                    "codec_name": "ac3",
                    "codec_tag": "0x0000",
                    "codec_tag_string": "[0][0][0][0]",
                    "codec_type": "audio",
                    "disposition": {
                        "attached_pic": 0,
                        "captions": 0,
                        "clean_effects": 0,
                        "comment": 0,
                        "default": 0,
                        "dependent": 0,
                        "descriptions": 0,
                        "dub": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "karaoke": 0,
                        "lyrics": 0,
                        "metadata": 0,
                        "original": 0,
                        "still_image": 0,
                        "timed_thumbnails": 0,
                        "visual_impaired": 0,
                    },
                    "index": 4,
                    "r_frame_rate": "0/0",
                    "sample_fmt": "fltp",
                    "sample_rate": "48000",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "tags": {
                        "BPS-eng": "192000",
                        "DURATION-eng": "00:23:38.112000000",
                        "NUMBER_OF_BYTES-eng": "34034688",
                        "NUMBER_OF_FRAMES-eng": "44316",
                        "SOURCE_ID-eng": "001101",
                        "_STATISTICS_TAGS-eng": "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID",
                        "_STATISTICS_WRITING_DATE_UTC-eng": "2021-04-21 20:00:45",
                        "language": "jpn",
                        "title": "Stereo",
                    },
                    "time_base": "1/1000",
                }
            ),
            AudioMatch(
                match_type=MatchType.LAST,
                match_item=MatchItem.ALL,
                match_input="*",
                conversion=None,
                bitrate="32k",
                downmix="No Downmix",
            ),
        ),
    ]

    assert result == expected_result, result


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
