# -*- coding: utf-8 -*-
from unittest import mock

from PySide6 import QtWidgets

from fastflix.widgets.panels.audio_panel import AudioList


def _make_list():
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app = mock.MagicMock()
    app.fastflix.config.theme = "onyx"
    parent = QtWidgets.QWidget()
    parent.main = mock.MagicMock()
    audio_list = AudioList(parent, app)
    tracks = []
    for _ in range(3):
        track = mock.MagicMock()
        tracks.append(track)
    audio_list.tracks = tracks
    return audio_list, tracks


def test_audio_panel_has_select_buttons():
    """Audio tab has the same Unselect All / Preserve All buttons as the subtitle tab."""
    audio_list, _ = _make_list()
    assert audio_list.remove_all_button.text()
    assert audio_list.save_all_button.text()


def test_unselect_and_preserve_all():
    audio_list, tracks = _make_list()
    audio_list.remove_all_button.click()
    for track in tracks:
        track.widgets.enable_check.setChecked.assert_called_with(False)
    audio_list.save_all_button.click()
    for track in tracks:
        track.widgets.enable_check.setChecked.assert_called_with(True)
