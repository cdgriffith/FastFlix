#!/usr/bin/env python
# -*- coding: utf-8 -*-

from qtpy import QtCore, QtWidgets


class StatusPanel(QtWidgets.QWidget):
    def __init__(self, parent, log_queue):
        super().__init__(parent)
        self.main = parent.main

        layout = QtWidgets.QGridLayout()
        self.inner_widget = Logs(self, log_queue)
        layout.addWidget(self.inner_widget)
        self.setLayout(layout)


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
