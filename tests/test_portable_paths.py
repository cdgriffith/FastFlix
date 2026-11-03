# -*- coding: utf-8 -*-
from fastflix.models.fastflix import FastFlix, portable_data_path


def test_portable_paths_stay_next_to_portable_config(tmp_path, monkeypatch):
    """#764: portable mode must not share queue.yaml / history / logs with an installed FastFlix in AppData."""
    monkeypatch.chdir(tmp_path)
    ff = FastFlix()
    default_queue = ff.queue_path
    ff.use_portable_paths()

    assert ff.data_path == tmp_path / "fastflix_data" == portable_data_path()
    assert ff.queue_path == tmp_path / "fastflix_data" / "queue.yaml"
    assert ff.log_path == tmp_path / "fastflix_data" / "logs"
    assert ff.queue_path != default_queue


def test_non_portable_paths_unchanged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ff = FastFlix()
    assert tmp_path not in ff.queue_path.parents
