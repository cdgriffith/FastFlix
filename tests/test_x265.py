# -*- coding: utf-8 -*-

from qtpy import QtCore, QtGui, QtWidgets


def test_sett():
    from pytestqt import qtbot

    from fastflix.encoders.common.setting_panel import SettingPanel
    from fastflix.widgets.container import Container

    main_app = QtWidgets.QApplication([])
    main_app.setStyle("fusion")
    main_app.setApplicationDisplayName("FastFlix")

    window = Container(
        flix=None,
        source="",
    )

    # panel = SettingPanel(None, None)
    # qtbot.addWidget(panel)

    # qtbot.mouseClick(panel.widgets.remove_hdr, QtCore.Qt.Key_Down)
    #
    # assert panel.widgets.remove_hdr == "yes"
    # assert True


def test_3():
    assert True
