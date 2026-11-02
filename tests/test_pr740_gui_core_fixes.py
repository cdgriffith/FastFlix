# -*- coding: utf-8 -*-
"""Regression tests for PR 740 review fixes (deinterlace presets, GOP, warnings, queue identity, ElidedLabel)."""

from pathlib import Path
from unittest import mock

import pytest
from PySide6 import QtWidgets

from fastflix.models.video import Video


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def advanced_panel(qapp):
    from fastflix.widgets.panels.advanced_panel import AdvancedPanel

    app = mock.MagicMock()
    app.fastflix.config.theme = "onyx"
    app.fastflix.config.suppress_video_speed_warning = False
    app.fastflix.config.suppress_reverse_video_warning = False
    app.fastflix.current_video = None
    parent = QtWidgets.QWidget()
    parent.main = mock.MagicMock()
    parent.main.loading_video = False
    panel = AdvancedPanel(parent, app)
    panel._parent_keepalive = parent
    return panel


def test_deinterlace_presets_explicit_modes():
    from fastflix.widgets.panels.advanced_panel import deinterlace_presets

    assert deinterlace_presets["yadif"] == {
        "send_frame": "yadif=mode=send_frame",
        "send_field": "yadif=mode=send_field",
    }
    assert deinterlace_presets["bwdif"] == {
        "send_frame": "bwdif=mode=send_frame",
        "send_field": "bwdif=mode=send_field",
    }
    assert deinterlace_presets["w3fdif"] == {"send_frame": "w3fdif=mode=frame", "send_field": "w3fdif=mode=field"}
    assert deinterlace_presets["estdif"] == {"send_frame": "estdif=mode=frame", "send_field": "estdif=mode=field"}


def test_gop_length_minimum_and_parsing(advanced_panel):
    w = advanced_panel.gop_length_widget
    assert w.validator().bottom() == 1
    for text, expected in [("", None), ("  ", None), ("0", None), ("-3", None), ("1", 1), ("250", 250)]:
        w.setText(text)
        assert advanced_panel.get_gop_length() == expected


def test_warnings_not_shown_for_programmatic_changes(advanced_panel):
    with mock.patch("fastflix.widgets.panels.advanced_panel.QtWidgets.QMessageBox") as box:
        advanced_panel.updating = True
        advanced_panel.reverse_video_widget.setChecked(True)
        advanced_panel.video_speed_widget.setCurrentIndex(1)
        advanced_panel.updating = False
        advanced_panel.main.loading_video = True
        advanced_panel.reverse_video_widget.setChecked(False)
        advanced_panel.reverse_video_widget.setChecked(True)
        advanced_panel.video_speed_widget.setCurrentIndex(2)
        assert not box.called


def test_warning_shown_for_user_change(advanced_panel):
    with mock.patch("fastflix.widgets.panels.advanced_panel.QtWidgets.QMessageBox") as box:
        advanced_panel.reverse_video_widget.setChecked(True)
        assert box.called


def test_refresh_video_identity(tmp_path):
    from fastflix.widgets.main_encoding import refresh_video_identity

    old = tmp_path / "old"
    old.mkdir()
    (old / "extra.txt").write_text("x")
    video = Video(source=Path("a.mkv"), work_path=old)
    old_uuid = video.uuid
    new = tmp_path / "new"
    refresh_video_identity(video, new)
    assert video.uuid != old_uuid
    assert video.work_path == new
    assert (new / "extra.txt").read_text() == "x"
    assert old.exists()


def test_elided_label_does_not_force_width(qapp):
    from fastflix.widgets.panels.queue_panel import ElidedLabel

    long_text = "A very long video title " * 20
    label = ElidedLabel(long_text)
    assert label.minimumSizeHint().width() <= ElidedLabel.MIN_WIDTH
    label.resize(120, 20)
    label.show()
    qapp.processEvents()
    assert label.text() != long_text
    assert label.text().endswith("\u2026")
    assert label.fullText() == long_text


def test_legacy_deinterlace_filters_map_to_presets():
    from fastflix.widgets.panels.advanced_panel import deinterlace_presets, legacy_deinterlace_filters

    assert legacy_deinterlace_filters["bwdif"] == ("bwdif", "send_frame")
    assert legacy_deinterlace_filters["yadif=mode=1"] == ("yadif", "send_field")
    assert legacy_deinterlace_filters["estdif=mode=1"] == ("estdif", "send_field")
    for method, mode in legacy_deinterlace_filters.values():
        assert mode in deinterlace_presets[method]
