# -*- coding: utf-8 -*-
"""Regression tests for GUI review fixes."""

from unittest import mock

import pytest
from PySide6 import QtWidgets


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_overwrite_prompt_escape_and_default_are_cancel(qapp):
    from fastflix.widgets.main_encoding import build_overwrite_prompt

    box, cancel, overwrite = build_overwrite_prompt()
    assert box.escapeButton() is cancel
    assert box.defaultButton() is cancel
    assert box.buttonRole(overwrite) == QtWidgets.QMessageBox.ButtonRole.AcceptRole
    assert box.buttonRole(cancel) == QtWidgets.QMessageBox.ButtonRole.RejectRole


def test_end_encoding_does_not_run_after_done():
    from fastflix.widgets.main_encoding import EncodingMixin

    fake = mock.MagicMock()
    EncodingMixin.end_encoding(fake)
    fake.video_options.queue.run_after_done.assert_not_called()


def test_conversion_complete_runs_after_done_only_on_success():
    from fastflix.widgets.main_encoding import EncodingMixin

    fake = mock.MagicMock()
    fake.app.fastflix.config.show_error_message = False
    EncodingMixin.conversion_complete(fake, False)
    fake.video_options.queue.run_after_done.assert_not_called()

    fake = mock.MagicMock()
    fake.app.fastflix.config.show_complete_message = False
    EncodingMixin.conversion_complete(fake, True)
    fake.video_options.queue.run_after_done.assert_called_once()


def test_notifier_does_not_process_events_off_thread():
    import inspect

    from fastflix.widgets.main_encoding import Notifier

    assert "processEvents" not in inspect.getsource(Notifier.run)


def test_run_preview_command_no_shell_with_timeout():
    from fastflix.widgets.windows import crop_window

    fake = mock.MagicMock(return_value=mock.MagicMock(returncode=0))
    cmd = ["ffmpeg", "-i", "a&b^c%d.mkv", "out.tiff"]
    with mock.patch.object(crop_window, "run", fake):
        result = crop_window.run_preview_command(cmd)
    assert result is fake.return_value
    assert fake.call_args.args[0] == cmd
    assert not fake.call_args.kwargs.get("shell")
    assert fake.call_args.kwargs["timeout"] > 0


def test_run_preview_command_timeout_returns_none():
    import subprocess

    from fastflix.widgets.windows import crop_window

    with mock.patch.object(crop_window, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 1)):
        assert crop_window.run_preview_command(["ffmpeg"]) is None


def test_large_preview_uses_shared_runner():
    import inspect

    from fastflix.widgets.windows import large_preview

    src = inspect.getsource(large_preview.LargePreview.generate_image)
    assert "shell=True" not in src
    assert "run_preview_command" in src


def test_dropped_local_path(qapp, tmp_path):
    from PySide6 import QtCore

    from fastflix.widgets.main import dropped_local_path

    f = tmp_path / "a.mkv"
    f.write_text("x")
    mime = QtCore.QMimeData()
    assert dropped_local_path(mime) is None

    mime.setUrls([QtCore.QUrl("https://example.com/x.mkv"), QtCore.QUrl.fromLocalFile(str(f))])
    assert dropped_local_path(mime) == f

    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl("https://example.com/x.mkv")])
    assert dropped_local_path(mime) is None


def test_thumbnail_requests_do_not_run_concurrently():
    from fastflix.widgets import main as main_mod

    fake = mock.MagicMock()
    fake._thumb_worker = None
    fake._thumb_pending = False
    with mock.patch.object(main_mod, "ThumbnailCreator") as creator:
        main_mod.Main._start_thumbnail_worker(fake, ["ffmpeg", "1"])
        main_mod.Main._start_thumbnail_worker(fake, ["ffmpeg", "2"])
        main_mod.Main._start_thumbnail_worker(fake, ["ffmpeg", "3"])
    assert creator.call_count == 1
    assert fake._thumb_pending is True

    worker = fake._thumb_worker
    main_mod.Main._thumbnail_worker_finished(fake)
    worker.deleteLater.assert_called_once()
    assert fake._thumb_worker is None
    assert fake._thumb_pending is False
    fake.generate_thumbnail.assert_called_once()


def test_field_change_debounced_only_when_user_is_typing():
    from fastflix.widgets import main as main_mod

    fake = mock.MagicMock()
    fake.sender.return_value.hasFocus.return_value = True
    main_mod.Main._field_changed(fake)
    fake._page_update_timer.start.assert_called_once()
    fake.page_update.assert_not_called()

    fake = mock.MagicMock()
    fake.sender.return_value.hasFocus.return_value = False
    main_mod.Main._field_changed(fake)
    fake.page_update.assert_called_once()
    fake._page_update_timer.start.assert_not_called()
