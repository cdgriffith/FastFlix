# -*- coding: utf-8 -*-
import queue
import sys
import time

import psutil
import pytest

from fastflix.command_runner import BackgroundRunner


class FakeProc:
    def __init__(self, returncode=None, children=(), pid=1):
        self.returncode = returncode
        self._children = list(children)
        self.pid = pid
        self.calls = []

    def poll(self):
        return self.returncode

    def children(self, recursive=False):
        self.calls.append(("children", recursive))
        return list(self._children)

    def terminate(self):
        self.calls.append("terminate")

    def kill(self):
        self.calls.append("kill")
        self.returncode = -9

    def suspend(self):
        self.calls.append("suspend")

    def resume(self):
        self.calls.append("resume")


def make_runner(tmp_path, returncode):
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.process = FakeProc(returncode=returncode)
    runner.output_file = tmp_path / "out.log"
    runner.error_output_file = tmp_path / "err.log"
    runner.output_file.write_text("")
    runner.error_output_file.write_text("")
    return runner


@pytest.mark.parametrize("code,expected", [(0, False), (1, True), (-9, True), (-11, True)])
def test_exit_code_marks_error(tmp_path, code, expected):
    runner = make_runner(tmp_path, code)
    runner.read_output()
    assert runner.error_detected is expected


def test_user_kill_is_not_an_error(tmp_path):
    runner = make_runner(tmp_path, -9)
    runner.killed = True
    runner.read_output()
    assert runner.error_detected is False


def test_kill_acts_on_whole_tree():
    grandchild = FakeProc(pid=3)
    child = FakeProc(pid=2)
    parent = FakeProc(children=[child, grandchild])
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.process = parent
    runner.kill(log=False)
    assert ("children", True) in parent.calls
    assert "kill" in child.calls and "kill" in grandchild.calls and "kill" in parent.calls
    assert runner.killed is True


def test_pause_resume_act_on_whole_tree():
    child = FakeProc(pid=2)
    parent = FakeProc(children=[child])
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.process = parent
    runner.pause()
    assert "suspend" in child.calls and "suspend" in parent.calls
    runner.resume()
    assert "resume" in child.calls and "resume" in parent.calls


def test_reader_survives_clean_race(tmp_path):
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.start_exec([sys.executable, "-c", "import time; time.sleep(0.3)"], work_dir=str(tmp_path))
    runner.clean()  # sets process to None while reader may still be running
    assert runner.process is None


@pytest.mark.skipif(sys.platform == "win32", reason="posix shell pipe")
def test_real_shell_tree_killed(tmp_path):
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.start_exec("sleep 30 | sleep 30", work_dir=str(tmp_path), shell=True)
    time.sleep(0.5)
    kids = runner.process.children(recursive=True)
    assert kids
    runner.kill(log=False)
    time.sleep(0.3)
    assert not any(k.is_running() and k.status() != psutil.STATUS_ZOMBIE for k in kids)


def test_real_nonzero_exit_flagged(tmp_path):
    runner = BackgroundRunner(log_queue=queue.Queue())
    runner.start_exec([sys.executable, "-c", "import sys; sys.exit(3)"], work_dir=str(tmp_path))
    runner.join_reader(timeout=5)
    assert runner.error_detected is True
