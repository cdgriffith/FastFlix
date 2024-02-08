# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from box import Box

from fastflix.application import init_encoders, create_app
from fastflix.models.config import Config

# from fastflix.widgets.container import Container

# import pytest

fake_app = Box(default_box=True)
fake_app.fastflix.config = Config()


def test_init_encoders():
    init_encoders(fake_app)
    assert "encoders" in fake_app.fastflix


# def test_app(qtbot):
#     # app = create_app(enable_scaling=False)
#     container = Container(MagicMock())
#     qtbot.addWidget(container)
#     from pytestqt.qt_compat import qt_api
#
#     qtbot.mouseClick(container.menuBar(), qt_api.QtCore.Qt.MouseButton.LeftButton)
#
#     assert container.menuBar().actions()[0].text() == "File"
#     #assert widget.greet_label.text() == "Hello!"


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


# Write a pytest for the Pyqt6 application defined in the fastflix/application.py file.
# def test_application():
#     app = create_app(enable_scaling=False)
