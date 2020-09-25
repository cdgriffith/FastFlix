#!/usr/bin/env python
# -*- coding: utf-8 -*-

from qtpy import QtCore, QtWidgets


class StatusPanel(QtWidgets.QWidget):
    def __init__(self, parent, log_queue):
        super().__init__(parent)
        self.main = parent.main

        layout = QtWidgets.QGridLayout()
        self.hide_nal = QtWidgets.QCheckBox("Hide NAL unit messages")
        self.hide_nal.setChecked(True)
        layout.addWidget(QtWidgets.QLabel("Encoder Output"), 0, 0)
        layout.addWidget(self.hide_nal, 0, 1, QtCore.Qt.AlignRight)
        self.inner_widget = Logs(self, log_queue)
        layout.addWidget(self.inner_widget, 1, 0, 1, 2)
        self.setLayout(layout)


class Logs(QtWidgets.QTextBrowser):
    log_signal = QtCore.Signal(str)
    clear_window = QtCore.Signal()

    def __init__(self, parent, log_queue):
        super(Logs, self).__init__(parent)
        self.status_panel = parent
        self.log_signal.connect(self.update_text)
        self.clear_window.connect(self.clear)

        LogUpdater(self, log_queue).start()

    def update_text(self, msg):
        if self.status_panel.hide_nal.isChecked() and msg.endswith(("NAL unit 62", "NAL unit 63")):
            return
        if self.status_panel.hide_nal.isChecked() and msg.lstrip().startswith("Last message repeated"):
            return
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
