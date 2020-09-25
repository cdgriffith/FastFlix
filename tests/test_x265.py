# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from qtpy import QtCore, QtGui, QtWidgets


def test_sett():
    # from pytestqt import qtbot
    from fastflix.encoders.common.setting_panel import SettingPanel
    from fastflix.gui import main

    mocker = MagicMock()
    # panel = settings_panel.SettingPanel(mocker, mocker)
    # qtbot.addWidget(panel)

    # qtbot.mouseClick(panel.widgets.remove_hdr, QtCore.Qt.Key_Down)

    # assert panel.widgets.remove_hdr == "yes"
    assert True


def test_3():
    assert True
