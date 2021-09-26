# -*- coding: utf-8 -*-
from box import Box

from fastflix.application import init_encoders
from fastflix.flix import ffmpeg_configuration
from fastflix.models.config import Config

fake_app = Box(default_box=True)
config = Config()


def test_init_encoders():
    init_encoders(fake_app)
    assert "encoders" in fake_app.fastflix


def test_get_ffmpeg_version():
    ffmpeg_configuration(fake_app, config)
    assert getattr(fake_app.fastflix, "ffmpeg_version")
    assert getattr(fake_app.fastflix, "ffmpeg_config")
