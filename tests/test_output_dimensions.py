# -*- coding: utf-8 -*-
"""Tests for Video.compute_output_dimensions and related properties."""

from pathlib import Path

from box import Box

from fastflix.models.video import Video, VideoSettings, Crop


class TestComputeOutputDimensions:
    """Test the static compute_output_dimensions method."""

    def test_auto_returns_none(self):
        assert Video.compute_output_dimensions(1920, 1080, method="auto") == (None, None)

    def test_auto_with_custom_returns_none(self):
        assert Video.compute_output_dimensions(1920, 1080, method="auto", custom="1280") == (None, None)

    def test_no_custom_returns_none(self):
        assert Video.compute_output_dimensions(1920, 1080, method="width", custom=None) == (None, None)

    def test_empty_custom_returns_none(self):
        assert Video.compute_output_dimensions(1920, 1080, method="width", custom="") == (None, None)

    # Width scaling
    def test_width_scaling_16_9(self):
        w, h = Video.compute_output_dimensions(3840, 2160, method="width", custom="1920")
        assert w == 1920
        assert h == 1080

    def test_width_scaling_4_3(self):
        w, h = Video.compute_output_dimensions(1440, 1080, method="width", custom="720")
        assert w == 720
        assert h == 536  # 1080*720/1440=540, rounded to nearest 8 = 536
        assert h % 8 == 0

    def test_width_scaling_ultrawide(self):
        w, h = Video.compute_output_dimensions(1920, 696, method="width", custom="1280")
        assert w == 1280
        assert h % 8 == 0

    # Height scaling
    def test_height_scaling_16_9(self):
        w, h = Video.compute_output_dimensions(3840, 2160, method="height", custom="1080")
        assert w == 1920
        assert h == 1080

    def test_height_scaling_4_3(self):
        w, h = Video.compute_output_dimensions(1440, 1080, method="height", custom="540")
        assert w == 720
        assert h == 540
        assert w % 8 == 0

    # Long edge scaling
    def test_long_edge_landscape(self):
        w, h = Video.compute_output_dimensions(3840, 2160, method="long edge", custom="1920")
        assert w == 1920
        assert h == 1080

    def test_long_edge_portrait(self):
        w, h = Video.compute_output_dimensions(2160, 3840, method="long edge", custom="1920")
        assert w == 1080
        assert h == 1920

    def test_long_edge_square(self):
        w, h = Video.compute_output_dimensions(1000, 1000, method="long edge", custom="500")
        assert w == 500
        assert h == 496  # 500 rounded down to nearest multiple of 8

    # Custom scaling
    def test_custom_explicit(self):
        w, h = Video.compute_output_dimensions(3840, 2160, method="custom", custom="1280:720")
        assert w == 1280
        assert h == 720

    def test_custom_invalid_format(self):
        assert Video.compute_output_dimensions(1920, 1080, method="custom", custom="1280") == (None, None)

    def test_custom_zero_dimension(self):
        assert Video.compute_output_dimensions(1920, 1080, method="custom", custom="0:720") == (None, None)

    # Rounding
    def test_rounding_to_multiple_of_8(self):
        # 1920x800 -> width=1280 -> height = 800*1280/1920 = 533.3 -> floor to 528
        w, h = Video.compute_output_dimensions(1920, 800, method="width", custom="1280")
        assert w == 1280
        assert h % 8 == 0

    def test_minimum_dimension_is_8(self):
        # Very extreme downscale — ensure minimum of 8
        w, h = Video.compute_output_dimensions(3840, 2160, method="width", custom="16")
        assert w == 16
        assert h >= 8
        assert h % 8 == 0

    # Crop
    def test_crop_affects_aspect_ratio(self):
        # 1920x1080, crop 100 from each side -> 1720x880
        # Scale width to 860 -> h = 880*860/1720 = 440
        w, h = Video.compute_output_dimensions(
            1920,
            1080,
            crop_top=100,
            crop_bottom=100,
            crop_left=100,
            crop_right=100,
            method="width",
            custom="860",
        )
        assert w == 860
        assert h == 440
        assert h % 8 == 0

    def test_crop_pillarbox_4_3_in_16_9(self):
        # 1920x1080 with 240px pillarbox on each side -> content is 1440x1080
        w, h = Video.compute_output_dimensions(
            1920,
            1080,
            crop_left=240,
            crop_right=240,
            method="width",
            custom="720",
        )
        assert w == 720
        # 1080*720/1440 = 540
        assert h == 536  # rounded to multiple of 8
        assert h % 8 == 0

    def test_crop_letterbox_ultrawide(self):
        # 1920x1080 with letterbox top/bottom -> content is 1920x696
        w, h = Video.compute_output_dimensions(
            1920,
            1080,
            crop_top=192,
            crop_bottom=192,
            method="width",
            custom="1920",
        )
        assert w == 1920
        assert h == 696
        assert h % 8 == 0

    def test_crop_exceeds_source_returns_none(self):
        assert Video.compute_output_dimensions(
            1920,
            1080,
            crop_left=1000,
            crop_right=1000,
            method="width",
            custom="100",
        ) == (None, None)

    # Invalid inputs
    def test_invalid_custom_string(self):
        assert Video.compute_output_dimensions(1920, 1080, method="width", custom="abc") == (None, None)

    def test_negative_pixels(self):
        assert Video.compute_output_dimensions(1920, 1080, method="width", custom="-100") == (None, None)

    def test_zero_pixels(self):
        assert Video.compute_output_dimensions(1920, 1080, method="width", custom="0") == (None, None)


class TestVideoOutputProperties:
    """Test the Video convenience properties that use compute_output_dimensions."""

    @staticmethod
    def make_video(width=1920, height=1080, crop=None, method="auto", custom=None):
        vs = VideoSettings(
            crop=crop,
            resolution_method=method,
            resolution_custom=custom,
        )
        return Video(
            source=Path("test.mkv"),
            duration=60,
            streams=Box({"video": [Box({"index": 0, "width": width, "height": height})]}),
            format=Box({}),
            video_settings=vs,
            work_path=Path("work"),
        )

    def test_cropped_width_no_crop(self):
        v = self.make_video()
        assert v.cropped_width == 1920

    def test_cropped_width_with_crop(self):
        v = self.make_video(crop=Crop(left=100, right=100))
        assert v.cropped_width == 1720

    def test_cropped_height_with_crop(self):
        v = self.make_video(crop=Crop(top=50, bottom=50))
        assert v.cropped_height == 980

    def test_output_width_auto(self):
        v = self.make_video()
        assert v.output_width is None
        assert v.output_height is None

    def test_output_width_with_scale(self):
        v = self.make_video(method="width", custom="960")
        assert v.output_width == 960
        assert v.output_height == 536  # 1080*960/1920 = 540 -> round to 536
        assert v.output_height % 8 == 0

    def test_scale_property_auto(self):
        v = self.make_video()
        assert v.scale is None

    def test_scale_property_with_dimensions(self):
        v = self.make_video(width=3840, height=2160, method="width", custom="1920")
        assert v.scale == "1920:1080"

    def test_scale_property_with_crop(self):
        v = self.make_video(
            crop=Crop(left=240, right=240),
            method="width",
            custom="720",
        )
        # Cropped: 1440x1080, scale width to 720 -> height = 1080*720/1440=540 -> round to 536
        assert v.scale == "720:536"
