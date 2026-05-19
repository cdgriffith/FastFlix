# -*- coding: utf-8 -*-
"""Tests for auto-crop detection parsing logic."""

from fastflix.flix import parse_cropdetect_output


def make_cropdetect_line(w, h, x, y):
    """Generate a realistic FFmpeg cropdetect output line."""
    return f"[Parsed_cropdetect_0 @ 0x55b8c0] x1:{x} x2:{x + w - 1} y1:{y} y2:{y + h - 1} w:{w} h:{h} x:{x} y:{y} pts:1001 t:1.001000 limit:0.094118 crop={w}:{h}:{x}:{y}"


def make_stderr(*detections):
    """Build a full stderr string from multiple (w, h, x, y) tuples."""
    lines = ["Input #0, matroska,webm, from 'test.mkv':"]
    for d in detections:
        lines.append(make_cropdetect_line(*d))
    return "\n".join(lines)


class TestParseCropdetectOutput:
    """Test parse_cropdetect_output with various aspect ratios and scenarios."""

    def test_16_9_letterbox_235_1(self):
        # 2.35:1 content in 1920x1080: top/bottom bars ~130px each
        # Content is ~1920x820
        stderr = make_stderr(
            (1920, 820, 0, 130),
            (1920, 818, 0, 131),
            (1920, 820, 0, 130),
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        # Most conservative = largest area = 1920*820
        assert result == [0, 130, 0, 130]  # [right, bottom, left, top]

    def test_4_3_pillarbox_in_16_9(self):
        # 4:3 content (1440x1080) in 1920x1080 frame with pillarboxing
        stderr = make_stderr(
            (1440, 1080, 240, 0),
            (1438, 1080, 241, 0),
            (1440, 1080, 240, 0),
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        # Most conservative = 1440*1080 (largest area)
        assert result == [240, 0, 240, 0]

    def test_ultrawide_276_1(self):
        # 2.76:1 content (1920x696) in 1920x1080 frame
        stderr = make_stderr(
            (1920, 696, 0, 192),
            (1920, 694, 0, 193),
            (1920, 696, 0, 192),
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result == [0, 192, 0, 192]

    def test_no_crop_needed(self):
        # Content fills entire frame
        stderr = make_stderr(
            (1920, 1080, 0, 0),
            (1920, 1080, 0, 0),
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result == [0, 0, 0, 0]

    def test_zero_offset_preserved(self):
        # x=0 and y=0 are valid offsets that should NOT be overwritten
        stderr = make_stderr(
            (1440, 1080, 240, 0),  # x=240, y=0 (y=0 is correct)
            (1438, 1078, 241, 1),  # Noisy: y=1 is wrong
            (1440, 1080, 240, 0),
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        # Should pick 1440*1080 (largest area), NOT mix y from frame 2
        assert result == [240, 0, 240, 0]

    def test_noisy_detections_picks_conservative(self):
        # Varying detections — should pick largest content area
        stderr = make_stderr(
            (1900, 1060, 10, 10),  # Slightly aggressive
            (1910, 1070, 5, 5),  # Less aggressive
            (1920, 1080, 0, 0),  # No crop (most conservative)
        )
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result == [0, 0, 0, 0]  # Picks the full frame

    def test_empty_stderr(self):
        result = parse_cropdetect_output("", 1920, 1080)
        assert result is None

    def test_no_cropdetect_lines(self):
        stderr = "Some other ffmpeg output\nNo cropdetect lines here"
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result is None

    def test_malformed_cropdetect_line(self):
        # One bad line mixed with good ones
        stderr = "[Parsed_cropdetect_0 @ 0x55b8c0] malformed=garbage\n" + make_cropdetect_line(1920, 800, 0, 140)
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result == [0, 140, 0, 140]

    def test_single_detection(self):
        stderr = make_stderr((1440, 1080, 240, 0))
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result == [240, 0, 240, 0]

    def test_negative_margin_returns_none(self):
        # Crop detection reports content larger than frame (shouldn't happen, but guard)
        stderr = make_stderr((2000, 1080, 0, 0))
        result = parse_cropdetect_output(stderr, 1920, 1080)
        assert result is None  # right = 1920 - 2000 - 0 = -80

    def test_4k_source(self):
        # 4K with letterbox
        stderr = make_stderr(
            (3840, 1600, 0, 280),
            (3840, 1602, 0, 279),
        )
        result = parse_cropdetect_output(stderr, 3840, 2160)
        # Most conservative: 3840*1602 > 3840*1600
        assert result == [0, 279, 0, 279]
