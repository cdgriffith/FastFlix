# -*- coding: utf-8 -*-
from fastflix.widgets.panels.subtitle_panel import parse_subtitle_filename_metadata


class TestParseSubtitleFilenameMetadata:
    def test_forced_german(self):
        result = parse_subtitle_filename_metadata("video", "video.forced.deu.srt", ".srt")
        assert result["language"] == "ger"
        assert result["dispositions"] == {"forced": True}
        assert result["title"] == "Forced"

    def test_sdh_german(self):
        result = parse_subtitle_filename_metadata("video", "video.sdh.deu.srt", ".srt")
        assert result["language"] == "ger"
        assert result["dispositions"] == {"hearing_impaired": True}
        assert result["title"] == "SDH"

    def test_normal_english(self):
        result = parse_subtitle_filename_metadata("video", "video.normal.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {}
        assert result["title"] == "Normal"

    def test_language_only(self):
        result = parse_subtitle_filename_metadata("video", "video.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {}
        assert result["title"] == ""

    def test_reversed_order(self):
        result = parse_subtitle_filename_metadata("video", "video.deu.forced.srt", ".srt")
        assert result["language"] == "ger"
        assert result["dispositions"] == {"forced": True}
        assert result["title"] == "Forced"

    def test_hi_treated_as_hearing_impaired(self):
        """'hi' should be treated as hearing_impaired disposition, not Hindi language."""
        result = parse_subtitle_filename_metadata("video", "video.hi.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"hearing_impaired": True}
        assert result["title"] == "SDH"

    def test_two_letter_language_code(self):
        result = parse_subtitle_filename_metadata("video", "video.de.srt", ".srt")
        assert result["language"] == "ger"
        assert result["dispositions"] == {}
        assert result["title"] == ""

    def test_no_segments(self):
        result = parse_subtitle_filename_metadata("video", "video.srt", ".srt")
        assert result["language"] == ""
        assert result["dispositions"] == {}
        assert result["title"] == ""

    def test_non_matching_stem(self):
        result = parse_subtitle_filename_metadata("video", "other_file.eng.srt", ".srt")
        assert result["language"] == ""
        assert result["dispositions"] == {}
        assert result["title"] == ""

    def test_multiple_dispositions(self):
        result = parse_subtitle_filename_metadata("video", "video.forced.sdh.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"forced": True, "hearing_impaired": True}
        # First disposition's title wins
        assert result["title"] == "Forced"

    def test_cc_tag(self):
        result = parse_subtitle_filename_metadata("video", "video.cc.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"hearing_impaired": True}
        assert result["title"] == "CC"

    def test_commentary_tag(self):
        result = parse_subtitle_filename_metadata("video", "video.commentary.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"comment": True}
        assert result["title"] == "Commentary"

    def test_ass_extension(self):
        result = parse_subtitle_filename_metadata("video", "video.forced.jpn.ass", ".ass")
        assert result["language"] == "jpn"
        assert result["dispositions"] == {"forced": True}
        assert result["title"] == "Forced"

    def test_unknown_segments_ignored(self):
        result = parse_subtitle_filename_metadata("video", "video.foobar.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {}
        assert result["title"] == ""

    def test_full_descriptor(self):
        result = parse_subtitle_filename_metadata("video", "video.full.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {}
        assert result["title"] == "Full"

    def test_video_stem_with_spaces(self):
        result = parse_subtitle_filename_metadata(
            "Beverly Hills Duck Pond - HDR10plus",
            "Beverly Hills Duck Pond - HDR10plus.forced.deu.srt",
            ".srt",
        )
        assert result["language"] == "ger"
        assert result["dispositions"] == {"forced": True}
        assert result["title"] == "Forced"

    def test_comment_tag(self):
        result = parse_subtitle_filename_metadata("video", "video.comment.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"comment": True}
        assert result["title"] == "Commentary"

    def test_default_disposition(self):
        result = parse_subtitle_filename_metadata("video", "video.default.eng.srt", ".srt")
        assert result["language"] == "eng"
        assert result["dispositions"] == {"default": True}
        assert result["title"] == ""
