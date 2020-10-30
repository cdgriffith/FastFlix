#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from qtpy import QtCore, QtWidgets

from fastflix.models.fastflix_app import FastFlixApp

splitter = re.compile(r"\s+[a-zA-Z]")


class StatusPanel(QtWidgets.QWidget):
    speed = QtCore.Signal(str)
    bitrate = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp, log_queue):
        super().__init__(parent)
        self.app = app
        self.main = parent.main

        layout = QtWidgets.QGridLayout()

        self.hide_nal = QtWidgets.QCheckBox("Hide NAL unit messages")
        self.hide_nal.setChecked(True)

        self.eta_label = QtWidgets.QLabel("ETA: N/A")
        self.eta_label.setToolTip("Estimated time left for current command")
        self.eta_label.setStyleSheet("QLabel{margin-right:50px}")
        self.size_label = QtWidgets.QLabel("Size Est: N/A")
        self.size_label.setToolTip("Estimated file size based on bitrate")

        h_box = QtWidgets.QHBoxLayout()
        h_box.addWidget(QtWidgets.QLabel("Encoder Output"), alignment=QtCore.Qt.AlignLeft)
        h_box.addStretch(1)
        h_box.addWidget(self.eta_label)
        h_box.addWidget(self.size_label)
        h_box.addStretch(1)
        h_box.addWidget(self.hide_nal, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(h_box, 0, 0)

        self.inner_widget = Logs(self, log_queue)
        layout.addWidget(self.inner_widget, 1, 0)
        self.setLayout(layout)

        self.speed.connect(self.update_speed)
        self.bitrate.connect(self.update_bitrate)

    def get_movie_length(self):
        return self.main.end_time - self.main.start_time

    def update_speed(self, combined):
        if not combined:
            self.eta_label.setText(f"ETA: N/A")
        try:
            time_passed, speed = combined.split("|")
            time_passed = self.main.time_to_number(time_passed)
            speed = float(speed)
            assert speed > 0.0001
            data = timedelta(seconds=(self.get_movie_length() - time_passed) // speed)
        except Exception:
            self.eta_label.setText(f"ETA: N/A")
        else:
            if not speed:
                self.eta_label.setText(f"ETA: N/A")
            self.eta_label.setText(f"ETA: {data}")

    def update_bitrate(self, bitrate):
        if not bitrate:
            self.size_label.setText(f"Size Est: N/A")
        try:
            bitrate, _ = bitrate.split("k", 1)
            bitrate = float(bitrate)
            size_eta = (self.get_movie_length() * bitrate) / 8000
        except Exception:
            self.size_label.setText(f"Size Est: N/A")
        else:
            if not size_eta:
                self.size_label.setText(f"Size Est: N/A")

            self.size_label.setText(f"Size Est: {size_eta:.2f}MB")


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
        if msg.startswith("frame="):
            try:
                details = [x.split("=") for x in splitter.split(msg)]
                self.status_panel.speed.emit(f"{details[-3][1].strip()}|{details[-1][1].strip().rstrip('x')}")
                self.status_panel.bitrate.emit(details[-2][1])
            except Exception:
                pass
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
