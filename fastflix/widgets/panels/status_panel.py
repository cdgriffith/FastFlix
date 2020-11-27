#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
from datetime import timedelta

from qtpy import QtCore, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import time_to_number
from fastflix.exceptions import FlixError

logger = logging.getLogger("fastflix")


class StatusPanel(QtWidgets.QWidget):
    speed = QtCore.Signal(str)
    bitrate = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.current_video: Video = None

        layout = QtWidgets.QGridLayout()

        self.hide_nal = QtWidgets.QCheckBox("Hide NAL unit messages")
        self.hide_nal.setChecked(True)

        self.eta_label = QtWidgets.QLabel(f"{t('Time Left')}: N/A")
        self.eta_label.setToolTip(t("Estimated time left for current command"))
        self.eta_label.setStyleSheet("QLabel{margin-right:50px}")
        self.size_label = QtWidgets.QLabel(f"{t('Size Estimate')}: N/A")
        self.size_label.setToolTip(t("Estimated file size based on bitrate"))

        h_box = QtWidgets.QHBoxLayout()
        h_box.addWidget(QtWidgets.QLabel("Encoder Output"), alignment=QtCore.Qt.AlignLeft)
        h_box.addStretch(1)
        h_box.addWidget(self.eta_label)
        h_box.addWidget(self.size_label)
        h_box.addStretch(1)
        h_box.addWidget(self.hide_nal, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(h_box, 0, 0)

        self.inner_widget = Logs(self, self.app, self.main, self.app.fastflix.log_queue)
        layout.addWidget(self.inner_widget, 1, 0)
        self.setLayout(layout)

        self.speed.connect(self.update_speed)
        self.bitrate.connect(self.update_bitrate)

    def get_movie_length(self):
        if not self.current_video:
            return
        return (
            self.current_video.video_settings.end_time or self.current_video.duration
        ) - self.current_video.video_settings.start_time

    def update_speed(self, combined):
        if not combined:
            self.eta_label.setText(f"{t('Time Left')}: N/A")
            return
        try:
            time_passed, speed = combined.split("|")
            time_passed = time_to_number(time_passed)
            speed = float(speed)
            if not speed:
                return
            assert speed > 0.0001
            length = self.get_movie_length()
            if not length:
                return
            data = timedelta(seconds=(length - time_passed) // speed)
        except Exception:
            logger.exception("can't update size ETA")
            self.eta_label.setText(f"{t('Time Left')}: N/A")
        else:
            if not speed:
                self.eta_label.setText(f"{t('Time Left')}: N/A")
            self.eta_label.setText(f"{t('Time Left')}: {data}")

    def update_bitrate(self, bitrate):
        if not bitrate or bitrate.strip() == "N/A":
            self.size_label.setText(f"{t('Size Estimate')}: N/A")
            return
        try:
            bitrate, _ = bitrate.split("k", 1)
            bitrate = float(bitrate)
            size_eta = (self.get_movie_length() * bitrate) / 8000
        except AttributeError:
            self.size_label.setText(f"{t('Size Estimate')}: N/A")
        except Exception:
            logger.exception(f"can't update bitrate: {bitrate}")
            self.size_label.setText(f"{t('Size Estimate')}: N/A")
        else:
            if not size_eta:
                self.size_label.setText(f"{t('Size Estimate')}: N/A")

            self.size_label.setText(f"{t('Size Estimate')}: {size_eta:.2f}MB")

    def update_title_bar(self):
        pass


class Logs(QtWidgets.QTextBrowser):
    log_signal = QtCore.Signal(str)
    clear_window = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp, main, log_queue):
        super(Logs, self).__init__(parent)
        self.parent = parent
        self.app = app
        self.main = main
        self.status_panel = parent
        self.current_video = None
        self.current_command = None
        self.log_signal.connect(self.update_text)
        self.clear_window.connect(self.blank)

        LogUpdater(self, log_queue).start()

    def update_text(self, msg):
        if self.status_panel.hide_nal.isChecked() and msg.endswith(("NAL unit 62", "NAL unit 63")):
            return
        if self.status_panel.hide_nal.isChecked() and msg.lstrip().startswith("Last message repeated"):
            return
        if msg.startswith("frame="):
            try:
                output = []
                for i in (x.strip().split() for x in msg.split("=")):
                    output.extend(i)

                frame = dict(zip(output[0::2], output[1::2]))

                self.status_panel.speed.emit(f"{frame.get('time', '')}|{frame.get('speed', '').rstrip('x')}")
                self.status_panel.bitrate.emit(frame.get("bitrate", ""))
            except Exception:
                pass
        self.append(msg)

    def blank(self, data):
        _, video_uuid, command_uuid = data.split(":")
        self.parent.current_video = self.main.find_video(video_uuid)
        try:
            self.current_command = self.main.find_command(self.parent.current_video, command_uuid)
        except FlixError:
            self.current_command = None
        self.setText("")
        self.parent.update_title_bar()

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
            if msg.startswith("CLEAR_WINDOW"):
                self.parent.clear_window.emit(msg)
            elif msg == "UPDATE_QUEUE":
                self.parent.status_panel.main.video_options.update_queue()
            else:
                self.parent.log_signal.emit(msg)
