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


def test_reindex_after_delete_shifts_later_tracks():
    from types import SimpleNamespace

    from fastflix.widgets.panels.audio_panel import reindex_after_delete

    tracks = [
        SimpleNamespace(index=0, disposition_widget=SimpleNamespace(track_index=0)),
        SimpleNamespace(index=2, disposition_widget=SimpleNamespace(track_index=2)),
        SimpleNamespace(index=3, disposition_widget=SimpleNamespace(track_index=3)),
    ]
    reindex_after_delete(tracks, 1)
    assert [x.index for x in tracks] == [0, 1, 2]
    assert [x.disposition_widget.track_index for x in tracks] == [0, 1, 2]


def test_del_me_reindexes_before_reorder():
    from types import SimpleNamespace

    from fastflix.widgets.panels.audio_panel import Audio

    remaining = SimpleNamespace(index=3, disposition_widget=SimpleNamespace(track_index=3))
    me = SimpleNamespace(index=2)
    audio_tracks = ["a", "b", "me", "c"]
    seen = {}
    parent = mock.MagicMock()
    parent.tracks = [me, remaining]
    parent.remove_track.side_effect = lambda w: seen.update(index=remaining.index, n=len(audio_tracks))
    me.parent = parent
    me.app = SimpleNamespace(fastflix=SimpleNamespace(current_video=SimpleNamespace(audio_tracks=audio_tracks)))
    Audio.del_me(me)
    assert audio_tracks == ["a", "b", "c"]
    assert seen == {"index": 2, "n": 3}


def test_call_with_timeout():
    import threading
    import time

    from fastflix.widgets.main_post_encode import call_with_timeout

    assert call_with_timeout(lambda x: x * 2, 1, 21) == 42
    release = threading.Event()
    start = time.time()
    with pytest.raises(TimeoutError):
        call_with_timeout(lambda: release.wait(5), 0.2)
    assert time.time() - start < 2
    release.set()
    with pytest.raises(ValueError):
        call_with_timeout(lambda: (_ for _ in ()).throw(ValueError("x")), 1)


def test_follow_progress_sleeps_when_idle_and_emits_frames():
    import io

    from fastflix.widgets.background_tasks import follow_progress

    f = io.StringIO("frame=1\nother\nframe=2\n")
    running = iter([True] * 6 + [False])
    emitted, sleeps = [], []
    follow_progress(lambda: next(running), f, emitted.append, sleep=sleeps.append)
    assert emitted == ["frame=1", "frame=2"]
    assert len(sleeps) >= 1


def test_show_log_dir_uses_desktop_services():
    from fastflix.widgets import container

    fake = mock.MagicMock()
    fake.app.fastflix.log_path = "C:/logs dir"
    with mock.patch.object(container.QtGui.QDesktopServices, "openUrl") as open_url:
        container.Container.show_log_dir(fake)
    url = open_url.call_args.args[0]
    assert url.isLocalFile()
    assert not hasattr(container, "OpenFolder")


def test_audio_title_is_synced_to_the_model_on_every_edit():
    """Typing a title then queueing without leaving the field must still use the typed title."""
    from types import SimpleNamespace

    from fastflix.widgets.panels.audio_panel import Audio

    track = SimpleNamespace(title="old")
    me = SimpleNamespace(
        index=0,
        title="typed title",
        app=SimpleNamespace(fastflix=SimpleNamespace(current_video=SimpleNamespace(audio_tracks=[track]))),
    )
    Audio.sync_title(me)
    assert track.title == "typed title"


def test_audio_title_sync_ignores_stale_index():
    from types import SimpleNamespace

    from fastflix.widgets.panels.audio_panel import Audio

    me = SimpleNamespace(
        index=5,
        title="x",
        app=SimpleNamespace(fastflix=SimpleNamespace(current_video=SimpleNamespace(audio_tracks=[]))),
    )
    Audio.sync_title(me)


def test_thumbnail_creator_gives_up_on_a_hung_ffmpeg():
    """A stuck thumbnail ffmpeg must finish (reporting failure) so queued thumbnail requests are not blocked forever."""
    import subprocess
    from types import SimpleNamespace

    from fastflix.widgets import background_tasks

    main = mock.MagicMock()
    fake = SimpleNamespace(main=main, command=["ffmpeg", "-i", "x"])
    with mock.patch.object(
        background_tasks, "run", side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)
    ) as run_mock:
        background_tasks.ThumbnailCreator.run(fake)
    assert run_mock.call_args.kwargs.get("timeout")
    main.thumbnail_complete.emit.assert_called_once_with(0)
