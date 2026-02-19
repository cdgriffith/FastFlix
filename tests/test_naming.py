# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from pathlib import Path

from box import Box

from fastflix.naming import (
    MAX_FILENAME_PATH_LENGTH,
    safe_format,
    resolve_pre_encode_variables,
    resolve_post_encode_variables,
    has_post_encode_placeholders,
    generate_preview,
    validate_template,
    truncate_filename,
    PRE_ENCODE_VARIABLES,
    POST_ENCODE_VARIABLES,
    ALL_VARIABLES,
)


class TestSafeFormat:
    def test_known_variables(self):
        result = safe_format("{source}-{encoder}", {"source": "MyMovie", "encoder": "x265"})
        assert result == "MyMovie-x265"

    def test_unknown_variables_left_as_is(self):
        result = safe_format("{source}-{unknown}", {"source": "MyMovie"})
        assert result == "MyMovie-{unknown}"

    def test_mixed_variables(self):
        result = safe_format("{source}-{foo}-{encoder}", {"source": "Test", "encoder": "x264"})
        assert result == "Test-{foo}-x264"

    def test_empty_template(self):
        result = safe_format("", {"source": "Test"})
        assert result == ""

    def test_no_variables(self):
        result = safe_format("plain-name", {"source": "Test"})
        assert result == "plain-name"

    def test_repeated_variable(self):
        result = safe_format("{source}-{source}", {"source": "Test"})
        assert result == "Test-Test"


class TestValidateTemplate:
    def test_valid_template(self):
        is_valid, msg = validate_template("{source}-{encoder}-{crf}")
        assert is_valid
        assert "Valid" in msg

    def test_empty_template(self):
        is_valid, msg = validate_template("")
        assert not is_valid
        assert "empty" in msg.lower()

    def test_unknown_variable(self):
        is_valid, msg = validate_template("{source}-{nonexistent}")
        assert not is_valid
        assert "nonexistent" in msg

    def test_multiple_unknown_variables(self):
        is_valid, msg = validate_template("{source}-{foo}-{bar}")
        assert not is_valid
        assert "foo" in msg
        assert "bar" in msg

    def test_all_variables_valid(self):
        template = "-".join(f"{{{v.name}}}" for v in ALL_VARIABLES)
        is_valid, msg = validate_template(template)
        assert is_valid

    def test_no_variables(self):
        is_valid, msg = validate_template("plain-name")
        assert is_valid

    def test_whitespace_only(self):
        is_valid, msg = validate_template("   ")
        assert not is_valid


class TestGeneratePreview:
    def test_basic_preview(self):
        result = generate_preview("{source}-{encoder}")
        assert "MyMovie" in result
        assert "x265" in result

    def test_all_variables_have_examples(self):
        template = "-".join(f"{{{v.name}}}" for v in ALL_VARIABLES)
        result = generate_preview(template)
        for var in ALL_VARIABLES:
            assert var.example in result


class TestResolvePreEncodeVariables:
    def test_basic_resolution(self):
        result = resolve_pre_encode_variables("{source}", Path("MyMovie.mkv"))
        assert result == "MyMovie"

    def test_source_with_special_chars(self):
        result = resolve_pre_encode_variables("{source}", Path("My Movie (2024).mkv"))
        assert "My Movie (2024)" in result

    def test_datetime_variables(self):
        result = resolve_pre_encode_variables("{date}-{time}", Path("test.mkv"))
        # Should contain date-like pattern
        assert "-" in result
        assert len(result) > 10

    def test_random_variables_different(self):
        result1 = resolve_pre_encode_variables("{rand_4}", Path("test.mkv"))
        result2 = resolve_pre_encode_variables("{rand_4}", Path("test.mkv"))
        # Random values should differ (extremely unlikely to match)
        assert result1 != result2

    def test_encoder_settings(self):
        class MockEncoder:
            name = "HEVC (x265)"
            preset = "slow"
            crf = 18
            bitrate = None
            pix_fmt = "yuv420p10le"

        result = resolve_pre_encode_variables(
            "{encoder}-{preset}-{crf}",
            Path("test.mkv"),
            encoder_settings=MockEncoder(),
        )
        assert "x265" in result
        assert "slow" in result
        assert "18" in result

    def test_no_encoder_settings_fallback(self):
        result = resolve_pre_encode_variables("{encoder}-{crf}", Path("test.mkv"))
        assert "N-A" in result

    def test_video_metadata(self):
        video = Box(
            {
                "width": 3840,
                "height": 2160,
                "duration": 5025,
                "frame_rate": "24000/1001",
                "color_space": "bt2020nc",
                "color_primaries": "bt2020",
                "color_transfer": "smpte2084",
                "hdr10_plus": [],
                "hdr10_streams": [{"index": 0}],
                "current_video_stream": {"codec_name": "hevc"},
                "format": {"bit_rate": "45000000"},
                "streams": {
                    "video": [{"index": 0, "codec_name": "hevc"}],
                    "audio": [{"codec_name": "aac", "channels": 6}],
                },
                "scale": None,
                "video_settings": {"selected_track": 0},
            }
        )
        result = resolve_pre_encode_variables(
            "{source_resolution}-{source_codec}-{hdr}",
            Path("test.mkv"),
            video=video,
        )
        assert "3840x2160" in result
        assert "hevc" in result
        assert "HDR10" in result

    def test_post_encode_placeholders_inserted(self):
        result = resolve_pre_encode_variables("{source}-{filesize}", Path("test.mkv"))
        assert "FFFSIZE" in result
        assert "test" in result

    def test_with_encoder_name_extraction(self):
        class MockEncoder:
            name = "AVC (x264)"
            preset = "medium"
            crf = 23
            bitrate = None
            pix_fmt = "yuv420p"

        result = resolve_pre_encode_variables("{encoder}", Path("test.mkv"), encoder_settings=MockEncoder())
        assert result == "x264"

    def test_encoder_name_no_parens(self):
        class MockEncoder:
            name = "gifski"
            preset = "default"

        result = resolve_pre_encode_variables("{encoder}", Path("test.mkv"), encoder_settings=MockEncoder())
        assert result == "gifski"


class TestResolvePostEncodeVariables:
    def test_basic_resolution(self):
        probe_data = Box(
            {
                "format": {"bit_rate": "5000000", "duration": "3600"},
                "streams": [
                    {"codec_type": "video", "bit_rate": "4500000"},
                    {"codec_type": "audio", "bit_rate": "320000"},
                ],
            }
        )
        start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 12, 15, 32, tzinfo=timezone.utc)

        result = resolve_post_encode_variables(
            "movie-FFETIME-FFVIDBIT",
            Path("dummy.mkv"),
            probe_data,
            encode_start=start,
            encode_end=end,
        )
        assert "00-15-32" in result
        assert "4500k" in result
        assert "FFETIME" not in result
        assert "FFVIDBIT" not in result

    def test_missing_probe_data(self):
        result = resolve_post_encode_variables(
            "movie-FFVIDBIT",
            Path("dummy.mkv"),
            None,
        )
        assert "N-A" in result

    def test_no_placeholders(self):
        result = resolve_post_encode_variables(
            "movie-output",
            Path("dummy.mkv"),
            None,
        )
        assert result == "movie-output"

    def test_filesize_placeholder(self, tmp_path):
        # Create a real file to test size
        test_file = tmp_path / "test.mkv"
        test_file.write_bytes(b"\x00" * (5 * 1024 * 1024))  # 5MB

        probe_data = Box({"format": {}, "streams": []})
        result = resolve_post_encode_variables(
            "movie-FFFSIZE-FFFSMB",
            test_file,
            probe_data,
        )
        assert "5.0MB" in result
        assert "FFFSIZE" not in result

    def test_all_placeholders_resolved(self):
        probe_data = Box(
            {
                "format": {"bit_rate": "5000000", "duration": "3600"},
                "streams": [
                    {"codec_type": "video", "bit_rate": "4500000"},
                    {"codec_type": "audio", "bit_rate": "320000"},
                ],
            }
        )
        start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 12, 15, 32, tzinfo=timezone.utc)

        # Build a filename with all placeholders
        filename = "-".join(var.placeholder for var in POST_ENCODE_VARIABLES)
        result = resolve_post_encode_variables(
            filename,
            Path("dummy.mkv"),
            probe_data,
            encode_start=start,
            encode_end=end,
        )
        # None of the placeholders should remain
        for var in POST_ENCODE_VARIABLES:
            assert var.placeholder not in result


class TestHasPostEncodePlaceholders:
    def test_with_placeholder(self):
        assert has_post_encode_placeholders("movie-FFETIME-output")

    def test_without_placeholder(self):
        assert not has_post_encode_placeholders("movie-output")

    def test_all_placeholders(self):
        for var in POST_ENCODE_VARIABLES:
            assert has_post_encode_placeholders(f"test-{var.placeholder}")

    def test_partial_match_no_false_positive(self):
        assert not has_post_encode_placeholders("movie-FF-output")


class TestTruncateFilename:
    def test_no_truncation_needed(self):
        name, was_truncated = truncate_filename("short-name", "C:\\Videos", ".mkv")
        assert name == "short-name"
        assert not was_truncated

    def test_truncation_applied(self):
        # Create a name that would exceed 250 with directory + extension
        long_name = "A" * 300
        name, was_truncated = truncate_filename(long_name, "C:\\Videos", ".mkv")
        assert was_truncated
        assert len(name) < 300
        # Full path should be within limit
        full_len = len("C:\\Videos") + 1 + len(name) + len(".mkv")
        assert full_len <= MAX_FILENAME_PATH_LENGTH

    def test_exact_limit(self):
        directory = "C:\\Videos"
        extension = ".mkv"
        # overhead = len(directory) + 1 + len(extension) = 9 + 1 + 4 = 14
        # max_name_len = 250 - 14 = 236
        exact_name = "A" * 236
        name, was_truncated = truncate_filename(exact_name, directory, extension)
        assert not was_truncated
        assert name == exact_name

    def test_one_over_limit(self):
        directory = "C:\\Videos"
        extension = ".mkv"
        over_name = "A" * 237
        name, was_truncated = truncate_filename(over_name, directory, extension)
        assert was_truncated
        assert len(name) == 236

    def test_long_directory_minimum_name(self):
        # Very long directory path
        long_dir = "C:\\" + "A" * 245
        name, was_truncated = truncate_filename("some-video-name", long_dir, ".mkv")
        # Should allow at least 10 chars for name
        assert len(name) >= 10

    def test_max_filename_path_length_constant(self):
        assert MAX_FILENAME_PATH_LENGTH == 250


class TestVariableRegistries:
    def test_all_variables_has_both(self):
        assert len(ALL_VARIABLES) == len(PRE_ENCODE_VARIABLES) + len(POST_ENCODE_VARIABLES)

    def test_unique_names(self):
        names = [v.name for v in ALL_VARIABLES]
        assert len(names) == len(set(names))

    def test_post_encode_have_placeholders(self):
        for var in POST_ENCODE_VARIABLES:
            assert var.placeholder
            assert var.placeholder.startswith("FF")
            assert var.placeholder.isalpha()

    def test_post_encode_placeholders_are_short(self):
        for var in POST_ENCODE_VARIABLES:
            assert len(var.placeholder) <= 8, (
                f"Placeholder {var.placeholder} is too long ({len(var.placeholder)} chars)"
            )

    def test_unique_placeholders(self):
        placeholders = [v.placeholder for v in POST_ENCODE_VARIABLES]
        assert len(placeholders) == len(set(placeholders))

    def test_pre_encode_no_placeholders(self):
        for var in PRE_ENCODE_VARIABLES:
            assert not var.placeholder
