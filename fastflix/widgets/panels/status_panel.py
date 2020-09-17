#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from box import Box

from qtpy import QtWidgets, QtCore, QtGui

from fastflix.shared import error_message, main_width
from fastflix.widgets.panels.abstract_list import FlixList


class StatusPanel(QtWidgets.QWidget):
    def __init__(self, parent, log_queue):
        super().__init__(parent)
        self.main = parent.main
        self.inner_layout = None

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Status"))

        # self.scroll_area = QtWidgets.QScrollArea(self)
        # self.scroll_area.setMinimumHeight(200)
        self.inner_widget = Logs(self, log_queue)
        layout.addWidget(self.inner_widget)
        self.setLayout(layout)

    # def init_inner(self):
    #     sp = QtWidgets.QSizePolicy()
    #     sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
    #     self.inner_widget.setSizePolicy(sp)
    #     self.scroll_area.setWidget(self.inner_widget)
    #     self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    #     self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)


class Logs(QtWidgets.QTextBrowser):
    log_signal = QtCore.Signal(str)
    clear_window = QtCore.Signal()

    def __init__(self, parent, log_queue):
        super(Logs, self).__init__(parent)

        self.log_signal.connect(self.update_text)
        self.clear_window.connect(self.clear)

        LogUpdater(self, log_queue).start()

    def update_text(self, msg):
        self.append(msg)

    def clear(self):
        self.setText("")

    def closeEvent(self, event):
        self.hide()
        # event.accept()


class LogUpdater(QtCore.QThread):
    def __init__(self, parent, log_queue):
        super().__init__(parent)
        self.parent = parent
        self.log_queue = log_queue

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            msg = self.log_queue.get()
            if msg == "CLEAR_WINDOW":
                self.parent.clear_window.emit()
            else:
                self.parent.log_signal.emit(msg)
