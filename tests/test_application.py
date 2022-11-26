# -*- coding: utf-8 -*-
from box import Box

from fastflix.application import init_encoders
from fastflix.models.config import Config

fake_app = Box(default_box=True)
fake_app.fastflix.config = Config()


def test_init_encoders():
    init_encoders(fake_app)
    assert "encoders" in fake_app.fastflix


# def test_get_ffmpeg_version():
#     ffmpeg_configuration(fake_app, fake_app.fastflix.config)
#     assert getattr(fake_app.fastflix, "ffmpeg_version")
#     assert getattr(fake_app.fastflix, "ffmpeg_config")
#
#
# def test_get_ffprobe_version():
#     ffprobe_configuration(fake_app, fake_app.fastflix.config)
#     assert getattr(fake_app.fastflix, "ffprobe_version")
#
#
# def test_get_audio_encoders():
#     ffmpeg_audio_encoders(fake_app, fake_app.fastflix.config)
#     assert len(getattr(fake_app.fastflix, "audio_encoders", [])) > 0
