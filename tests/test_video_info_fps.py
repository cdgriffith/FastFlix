# -*- coding: utf-8 -*-
import pytest

from fastflix.widgets.main_video_load import VideoLoadMixin


@pytest.mark.parametrize(
    "stream,expected",
    [
        ({"avg_frame_rate": "24000/1001", "r_frame_rate": "24000/1001"}, "23.976 fps"),
        ({"avg_frame_rate": "25/1"}, "25 fps"),
        ({"avg_frame_rate": "30000/1001"}, "29.97 fps"),
        ({"avg_frame_rate": "0/0", "r_frame_rate": "60/1"}, "60 fps"),
        ({"avg_frame_rate": "", "r_frame_rate": "bad"}, ""),
        ({}, ""),
    ],
)
def test_fps_from_stream(stream, expected):
    """#747: show the source frame rate in Video Info."""
    assert VideoLoadMixin._fps_from_stream(stream) == expected
