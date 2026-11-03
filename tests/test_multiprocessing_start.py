# -*- coding: utf-8 -*-
from unittest import mock

import fastflix.__main__ as ff_main


def _run(platform, current=None):
    with (
        mock.patch.object(ff_main.sys, "platform", platform),
        mock.patch.object(ff_main.multiprocessing, "get_start_method", return_value=current),
        mock.patch.object(ff_main.multiprocessing, "set_start_method") as set_method,
    ):
        ff_main.configure_multiprocessing()
    return set_method


def test_linux_uses_fork_instead_of_forkserver():
    """#750: Python 3.14's forkserver default re-launched frozen FastFlix builds endlessly on Linux."""
    _run("linux").assert_called_once_with("fork")


def test_other_platforms_and_explicit_methods_untouched():
    _run("win32").assert_not_called()
    _run("darwin").assert_not_called()
    _run("linux", current="spawn").assert_not_called()
