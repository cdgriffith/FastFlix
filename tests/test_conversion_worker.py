# -*- coding: utf-8 -*-
import queue

import pytest

from fastflix import conversion_worker


class FakeRunner:
    instances = []

    def __init__(self, log_queue):
        self.process = type("P", (), {"returncode": -9})()
        self.error_detected = False
        self.killed = False
        self.kill_calls = 0
        self.alive = True
        self.joined = False
        FakeRunner.instances.append(self)

    def is_alive(self):
        return self.alive

    def start_exec(self, *a, **k):
        self.alive = False

    def change_priority(self, *_):
        pass

    def join_reader(self, timeout=1.0):
        self.joined = True

    def kill(self, log=True):
        self.kill_calls += 1
        self.killed = True


class FakeGui:
    def __init__(self, alive=True):
        self.alive = alive

    def is_alive(self):
        return self.alive

    def join(self):
        pass


class FakeLogQueue:
    def __init__(self):
        self.items = []
        self.cancelled = False

    def put(self, item, timeout=None):
        self.items.append(item)

    def cancel_join_thread(self):
        self.cancelled = True


@pytest.fixture(autouse=True)
def patch_runner(monkeypatch):
    FakeRunner.instances = []
    monkeypatch.setattr(conversion_worker, "BackgroundRunner", FakeRunner)
    monkeypatch.setattr(conversion_worker.reusables, "remove_file_handlers", lambda *_: None)
    monkeypatch.setattr(
        conversion_worker.reusables, "get_file_handler", lambda *a, **k: conversion_worker.logging.NullHandler()
    )


def run(requests, gui=None, log_queue=None):
    wq, sq = queue.Queue(), queue.Queue()
    for r in requests:
        wq.put(r)
    lq = log_queue or FakeLogQueue()
    conversion_worker.queue_worker(gui or FakeGui(), wq, sq, lq)
    out = []
    while not sq.empty():
        out.append(sq.get())
    return out, lq


def test_negative_return_code_reported_as_error():
    out, _ = run([("execute", "v", "c", "cmd", "wd", "n", False), ("shutdown",)])
    assert out[0][0] == "error"


def test_killed_negative_code_not_error(monkeypatch):
    class KilledRunner(FakeRunner):
        def start_exec(self, *a, **k):
            self.alive = False
            self.killed = True

    monkeypatch.setattr(conversion_worker, "BackgroundRunner", KilledRunner)
    out, _ = run([("execute", "v", "c", "cmd", "wd", "n", False), ("shutdown",)])
    assert out[0][0] == "complete"


def test_runner_killed_if_worker_raises(monkeypatch):
    class Boom(FakeGui):
        def is_alive(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run([], gui=Boom())
    assert FakeRunner.instances[0].kill_calls >= 1


def test_log_queue_join_cancelled_when_gui_dies(monkeypatch):
    monkeypatch.setattr(FakeRunner, "is_alive", lambda self: False)
    _, lq = run([], gui=FakeGui(alive=False))
    assert lq.cancelled is True
