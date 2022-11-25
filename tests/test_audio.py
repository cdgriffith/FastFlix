from box import Box

from fastflix.models.profiles import AudioMatch, MatchType, MatchItem

from fastflix.audio_processing import apply_audio_filters

from .general import test_audio_tracks


def test_audio_filters():
    test_filters = [
        AudioMatch(match_type=MatchType.FIRST, match_item=MatchItem.TITLE, match_input='Surround 5', conversion=None,
                   bitrate='32k', downmix='No Downmix'),
        AudioMatch(match_type=MatchType.LAST, match_item=MatchItem.ALL, match_input='*', conversion=None, bitrate='32k',
                   downmix='No Downmix'),
        AudioMatch(match_type=MatchType.ALL, match_item=MatchItem.LANGUAGE, match_input='eng', conversion=None,
                   bitrate='32k', downmix='No Downmix')]

    result = apply_audio_filters(audio_filters=test_filters, original_tracks=test_audio_tracks)

    expected_result = [
        (Box({'avg_frame_rate': '0/0', 'bits_per_raw_sample': '24', 'bits_per_sample': 0, 'channel_layout': '5.1(side)',
              'channels': 6, 'codec_long_name': 'TrueHD', 'codec_name': 'truehd', 'codec_tag': '0x0000',
              'codec_tag_string': '[0][0][0][0]', 'codec_type': 'audio',
              'disposition': {'attached_pic': 0, 'captions': 0, 'clean_effects': 0, 'comment': 0, 'default': 0,
                              'dependent': 0, 'descriptions': 0, 'dub': 0, 'forced': 0, 'hearing_impaired': 0,
                              'karaoke': 0, 'lyrics': 0, 'metadata': 0, 'original': 0, 'still_image': 0,
                              'timed_thumbnails': 0, 'visual_impaired': 0}, 'index': 1, 'r_frame_rate': '0/0',
              'sample_fmt': 's32', 'sample_rate': '48000', 'start_pts': 0, 'start_time': '0.000000',
              'tags': {'BPS-eng': '1921846', 'DURATION-eng': '00:23:38.083333333', 'NUMBER_OF_BYTES-eng': '340667312',
                       'NUMBER_OF_FRAMES-eng': '1701700', 'SOURCE_ID-eng': '001100',
                       '_STATISTICS_TAGS-eng': 'BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID',
                       '_STATISTICS_WRITING_DATE_UTC-eng': '2021-04-21 20:00:45', 'language': 'eng',
                       'title': 'Surround 5.1'}, 'time_base': '1/1000'}),
         AudioMatch(match_type=MatchType.FIRST, match_item=MatchItem.TITLE, match_input='Surround 5', conversion=None,
                    bitrate='32k', downmix='No Downmix')),
        (Box({'avg_frame_rate': '0/0', 'bits_per_raw_sample': '24', 'bits_per_sample': 0, 'channel_layout': '5.1(side)',
              'channels': 6, 'codec_long_name': 'TrueHD', 'codec_name': 'truehd', 'codec_tag': '0x0000',
              'codec_tag_string': '[0][0][0][0]', 'codec_type': 'audio',
              'disposition': {'attached_pic': 0, 'captions': 0, 'clean_effects': 0, 'comment': 0, 'default': 0,
                              'dependent': 0, 'descriptions': 0, 'dub': 0, 'forced': 0, 'hearing_impaired': 0,
                              'karaoke': 0, 'lyrics': 0, 'metadata': 0, 'original': 0, 'still_image': 0,
                              'timed_thumbnails': 0, 'visual_impaired': 0}, 'index': 1, 'r_frame_rate': '0/0',
              'sample_fmt': 's32', 'sample_rate': '48000', 'start_pts': 0, 'start_time': '0.000000',
              'tags': {'BPS-eng': '1921846', 'DURATION-eng': '00:23:38.083333333', 'NUMBER_OF_BYTES-eng': '340667312',
                       'NUMBER_OF_FRAMES-eng': '1701700', 'SOURCE_ID-eng': '001100',
                       '_STATISTICS_TAGS-eng': 'BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID',
                       '_STATISTICS_WRITING_DATE_UTC-eng': '2021-04-21 20:00:45', 'language': 'eng',
                       'title': 'Surround 5.1'}, 'time_base': '1/1000'}),
         AudioMatch(match_type=MatchType.ALL, match_item=MatchItem.LANGUAGE, match_input='eng', conversion=None,
                    bitrate='32k', downmix='No Downmix')),
        (Box({'avg_frame_rate': '0/0', 'bit_rate': '448000', 'bits_per_sample': 0, 'channel_layout': '5.1(side)',
              'channels': 6, 'codec_long_name': 'ATSC A/52A (AC-3)', 'codec_name': 'ac3', 'codec_tag': '0x0000',
              'codec_tag_string': '[0][0][0][0]', 'codec_type': 'audio',
              'disposition': {'attached_pic': 0, 'captions': 0, 'clean_effects': 0, 'comment': 0, 'default': 0,
                              'dependent': 0, 'descriptions': 0, 'dub': 0, 'forced': 0, 'hearing_impaired': 0,
                              'karaoke': 0, 'lyrics': 0, 'metadata': 0, 'original': 0, 'still_image': 0,
                              'timed_thumbnails': 0, 'visual_impaired': 0}, 'index': 2, 'r_frame_rate': '0/0',
              'sample_fmt': 'fltp', 'sample_rate': '48000', 'start_pts': 0, 'start_time': '0.000000',
              'tags': {'BPS-eng': '448000', 'DURATION-eng': '00:23:38.112000000', 'NUMBER_OF_BYTES-eng': '79414272',
                       'NUMBER_OF_FRAMES-eng': '44316', 'SOURCE_ID-eng': '001100',
                       '_STATISTICS_TAGS-eng': 'BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID',
                       '_STATISTICS_WRITING_DATE_UTC-eng': '2021-04-21 20:00:45', 'language': 'eng',
                       'title': 'Surround 5.1'}, 'time_base': '1/1000'}),
         AudioMatch(match_type=MatchType.ALL, match_item=MatchItem.LANGUAGE, match_input='eng', conversion=None,
                    bitrate='32k', downmix='No Downmix')),
        (Box({'avg_frame_rate': '0/0', 'bit_rate': '192000', 'bits_per_sample': 0, 'channel_layout': 'stereo',
              'channels': 2, 'codec_long_name': 'ATSC A/52A (AC-3)', 'codec_name': 'ac3', 'codec_tag': '0x0000',
              'codec_tag_string': '[0][0][0][0]', 'codec_type': 'audio',
              'disposition': {'attached_pic': 0, 'captions': 0, 'clean_effects': 0, 'comment': 0, 'default': 0,
                              'dependent': 0, 'descriptions': 0, 'dub': 0, 'forced': 0, 'hearing_impaired': 0,
                              'karaoke': 0, 'lyrics': 0, 'metadata': 0, 'original': 0, 'still_image': 0,
                              'timed_thumbnails': 0, 'visual_impaired': 0}, 'index': 4, 'r_frame_rate': '0/0',
              'sample_fmt': 'fltp', 'sample_rate': '48000', 'start_pts': 0, 'start_time': '0.000000',
              'tags': {'BPS-eng': '192000', 'DURATION-eng': '00:23:38.112000000', 'NUMBER_OF_BYTES-eng': '34034688',
                       'NUMBER_OF_FRAMES-eng': '44316', 'SOURCE_ID-eng': '001101',
                       '_STATISTICS_TAGS-eng': 'BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES SOURCE_ID',
                       '_STATISTICS_WRITING_DATE_UTC-eng': '2021-04-21 20:00:45', 'language': 'jpn', 'title': 'Stereo'},
              'time_base': '1/1000'}),
         AudioMatch(match_type=MatchType.LAST, match_item=MatchItem.ALL, match_input='*', conversion=None,
                    bitrate='32k', downmix='No Downmix')),
    ]

    assert result == expected_result, result
