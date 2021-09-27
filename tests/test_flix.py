# -*- coding: utf-8 -*-
from pathlib import Path

from box import Box

from fastflix.flix import parse, parse_hdr_details
from fastflix.models.config import Config
from fastflix.models.video import Video

fake_app = Box(default_box=True)
fake_app.fastflix.config = Config()


def test_parse():
    fake_app.fastflix.current_video = Video(
        source=Path("tests", "media", "Beverly Hills Duck Pond - HDR10plus - Jessica Payne.mp4")
    )
    parse(fake_app)
    assert fake_app.fastflix.current_video.streams.video[0].codec_name == "hevc"
    assert fake_app.fastflix.current_video.streams.video[0].coded_width == 1920
    assert fake_app.fastflix.current_video.streams.video[0].coded_height == 1088
    assert fake_app.fastflix.current_video.streams.video[0].r_frame_rate == "30/1"
    assert fake_app.fastflix.current_video.streams.audio[0].codec_name == "aac"
    parse_hdr_details(fake_app)
    assert len(fake_app.fastflix.current_video.hdr10_streams) == 1
