# -*- coding: utf-8 -*-
from subprocess import CompletedProcess, TimeoutExpired
from unittest import mock

from fastflix import rigaya_helpers
from fastflix.rigaya_helpers import run_check_features


def completed(returncode=0, stdout="#0: GPU (1 SM)\nCodec: H.264\n", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_stderr_output_does_not_abort_device_detection():
    """Warnings on stderr (very common with the encoder binaries) must not hide a working device."""
    side_effect = [completed(stderr="some warning"), completed(stderr="another"), completed(returncode=1, stdout="")]
    with mock.patch.object(rigaya_helpers, "run", side_effect=side_effect):
        outputs = run_check_features("NVEncC64")
    assert len(outputs) == 2


def test_stops_at_first_failing_device():
    side_effect = [completed(), completed(returncode=1, stdout=""), completed()]
    with mock.patch.object(rigaya_helpers, "run", side_effect=side_effect) as run:
        outputs = run_check_features("NVEncC64")
    assert len(outputs) == 1
    assert run.call_count == 2


def test_timeout_is_passed_and_handled(caplog):
    with mock.patch.object(rigaya_helpers, "run", side_effect=TimeoutExpired(cmd="x", timeout=1)) as run:
        with caplog.at_level("WARNING", logger="fastflix"):
            outputs = run_check_features("NVEncC64")
    assert outputs == []
    assert run.call_args.kwargs["timeout"] > 0
    assert "NVEncC64" in caplog.text


def test_missing_executable_is_logged(caplog):
    with mock.patch.object(rigaya_helpers, "run", side_effect=FileNotFoundError("nope")):
        with caplog.at_level("WARNING", logger="fastflix"):
            assert run_check_features("NVEncC64", is_qsv=True) == []
    assert "NVEncC64" in caplog.text


def test_qsv_failure_returns_no_devices(caplog):
    with mock.patch.object(rigaya_helpers, "run", return_value=completed(returncode=2, stdout="")):
        with caplog.at_level("WARNING", logger="fastflix"):
            assert run_check_features("QSVEncC64", is_qsv=True) == []
    assert "QSVEncC64" in caplog.text


def test_qsv_success_with_stderr():
    with mock.patch.object(rigaya_helpers, "run", return_value=completed(stderr="warn")):
        assert len(run_check_features("QSVEncC64", is_qsv=True)) == 1
