# -*- coding: utf-8 -*-
from unittest import mock

import pytest
from PySide6 import QtWidgets

from fastflix.encoders.ffmpeg_av1_nvenc.settings_panel import AV1NVENC
from fastflix.encoders.ffmpeg_hevc_nvenc.settings_panel import NVENC
from fastflix.models.encode import FFmpegAV1NVENCSettings, FFmpegNVENCSettings

PANELS = [(NVENC, FFmpegNVENCSettings, "ffmpeg_hevc_nvenc"), (AV1NVENC, FFmpegAV1NVENCSettings, "ffmpeg_av1_nvenc")]


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _make_panel(panel_cls, settings_cls, saved, qapp):
    app = mock.MagicMock()
    app.fastflix.config.encoder_opt.side_effect = lambda _name, opt: getattr(saved, opt)
    main = mock.MagicMock()
    panel = panel_cls(None, main, app)
    return panel, app


@pytest.mark.parametrize("panel_cls,settings_cls,name", PANELS)
def test_panel_round_trips_defaults(panel_cls, settings_cls, name, qapp):
    defaults = settings_cls()
    panel, app = _make_panel(panel_cls, settings_cls, defaults, qapp)
    panel.update_video_encoder_settings()
    result = app.fastflix.current_video.video_settings.video_encoder_settings
    for field in (
        "preset",
        "aq_strength",
        "tf_level",
        "lookahead_level",
        "split_encode_mode",
        "weighted_pred",
        "no_scenecut",
        "temporal_aq",
        "multipass",
        "cq",
    ):
        if hasattr(defaults, field):
            assert getattr(result, field) == getattr(defaults, field), field


@pytest.mark.parametrize("panel_cls,settings_cls,name", PANELS)
def test_panel_loads_saved_values(panel_cls, settings_cls, name, qapp):
    saved = settings_cls(tf_level="4", lookahead_level="2", split_encode_mode="forced", weighted_pred=1, cq=30)
    saved.aq_strength = 12
    saved.no_scenecut = True
    panel, app = _make_panel(panel_cls, settings_cls, saved, qapp)
    panel.update_video_encoder_settings()
    result = app.fastflix.current_video.video_settings.video_encoder_settings
    assert (result.tf_level, result.lookahead_level, result.split_encode_mode) == ("4", "2", "forced")
    assert (result.weighted_pred, result.cq, result.aq_strength, result.no_scenecut) == (1, 30, 12, True)
