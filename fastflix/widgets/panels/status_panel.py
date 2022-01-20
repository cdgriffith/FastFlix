#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import time
from datetime import timedelta
from typing import Optional

from PySide6 import QtCore, QtWidgets

from fastflix.exceptions import FlixError
from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.shared import time_to_number, timedelta_to_str

logger = logging.getLogger("fastflix")


class StatusPanel(QtWidgets.QWidget):
    speed = QtCore.Signal(str)
    bitrate = QtCore.Signal(str)
    nvencc_signal = QtCore.Signal(str)
    tick_signal = QtCore.Signal()

    def __init__(self, parent, app: FastFlixApp):
        super().__init__(parent)
        self.app = app
        self.main = parent.main
        self.current_video: Optional[Video] = None
        self.started_at = None

        self.ticker_thread = ElapsedTimeTicker(self, self.tick_signal)
        self.ticker_thread.start()

        layout = QtWidgets.QGridLayout()

        self.hide_nal = QtWidgets.QCheckBox(t("Hide NAL unit messages"))
        self.hide_nal.setChecked(True)

        self.eta_label = QtWidgets.QLabel(f"{t('Time Left')}: N/A")
        self.eta_label.setToolTip(t("Estimated time left for current command"))
        self.eta_label.setStyleSheet("QLabel{margin-right:50px}")
        self.time_elapsed_label = QtWidgets.QLabel(f"{t('Time Elapsed')}: N/A")
        self.time_elapsed_label.setStyleSheet("QLabel{margin-right:50px}")
        self.size_label = QtWidgets.QLabel(f"{t('Size Estimate')}: N/A")
        self.size_label.setToolTip(t("Estimated file size based on bitrate"))

        h_box = QtWidgets.QHBoxLayout()
        h_box.addWidget(QtWidgets.QLabel(t("Encoder Output")), alignment=QtCore.Qt.AlignLeft)
        h_box.addStretch(1)
        h_box.addWidget(self.eta_label)
        h_box.addWidget(self.time_elapsed_label)
        h_box.addWidget(self.size_label)
        h_box.addStretch(1)
        h_box.addWidget(self.hide_nal, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(h_box, 0, 0)

        self.inner_widget = Logs(self, self.app, self.main, self.app.fastflix.log_queue)
        layout.addWidget(self.inner_widget, 1, 0)
        self.setLayout(layout)

        self.speed.connect(self.update_speed)
        self.bitrate.connect(self.update_bitrate)
        self.nvencc_signal.connect(self.update_nvencc)
        self.main.status_update_signal.connect(self.on_status_update)
        self.tick_signal.connect(self.update_time_elapsed)

    def cleanup(self):
        self.inner_widget.log_updater.terminate()
        self.ticker_thread.stop_signal.emit()
        self.ticker_thread.terminate()

    def get_movie_length(self):
        if not self.current_video:
            return 0
        return (
            self.current_video.video_settings.end_time or self.current_video.duration
        ) - self.current_video.video_settings.start_time

    def update_speed(self, combined):
        if not combined:
            self.eta_label.setText(f"{t('Time Left')}: N/A")
            return
        try:
            time_passed, speed = combined.split("|")
            if speed == "N/A":
                self.eta_label.setText(f"{t('Time Left')}: N/A")
                return
            time_passed = time_to_number(time_passed)
            speed = float(speed)
            if not speed:
                return
            assert speed > 0.0001, speed
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
            self.eta_label.setText(f"{t('Time Left')}: {timedelta_to_str(data)}")

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
            logger.exception(f"can't update bitrate: {bitrate} - length {self.get_movie_length()}")
            self.size_label.setText(f"{t('Size Estimate')}: N/A")
        else:
            if not size_eta:
                self.size_label.setText(f"{t('Size Estimate')}: N/A")

            self.size_label.setText(f"{t('Size Estimate')}: {size_eta:.2f}MB")

    def update_nvencc(self, raw_line):
        """
        Example line:
        [53.1%] 19/35 frames: 150.57 fps, 5010 kb/s, remain 0:01:55, GPU 10%, VE 96%, VD 42%, est out size 920.6MB
        """
        for section in raw_line.split(","):
            section = section.strip()
            if section.startswith("remain"):
                self.eta_label.setText(f"{t('Time Left')}: {section.rsplit(maxsplit=1)[1]}")
            elif section.startswith("est out size"):
                self.size_label.setText(f"{t('Size Estimate')}: {section.rsplit(maxsplit=1)[1]}")

    def update_time_elapsed(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        if not self.started_at:
            logger.warning("Unable to update time elapsed because start time isn't set")
            return

        try:
            time_elapsed = now - self.started_at
        except Exception:
            logger.exception("Unable to calculate elapsed time")
            return

        self.time_elapsed_label.setText(f"{t('Time Elapsed')}: {timedelta_to_str(time_elapsed)}")

    def on_status_update(self):
        # If there was a status change, we need to restart ticker no matter what
        self.started_at = datetime.datetime.now(datetime.timezone.utc)

    def close(self):
        self.ticker_thread.terminate()
        super().close()


class Logs(QtWidgets.QTextBrowser):
    log_signal = QtCore.Signal(str)
    clear_window = QtCore.Signal(str)
    timer_signal = QtCore.Signal(str)

    def __init__(self, parent, app: FastFlixApp, main, log_queue):
        super(Logs, self).__init__(parent)
        self.parent = parent
        self.app = app
        self.main = main
        self.status_panel = parent
        self.current_video = None
        self.log_signal.connect(self.update_text)
        self.clear_window.connect(self.blank)
        self.timer_signal.connect(self.timer_update)

        self.log_updater = LogUpdater(self, log_queue)
        self.log_updater.start()

    def update_text(self, msg):
        if self.status_panel.hide_nal.isChecked() and msg.endswith(("NAL unit 62", "NAL unit 63")):
            return
        if self.status_panel.hide_nal.isChecked() and msg.lstrip().startswith("Last message repeated"):
            return
        if msg.startswith("frame="):
            try:
                frame = {}
                output = [i for i in (x.strip().split() for x in msg.split("="))]
                output[-1].append([])  # no final value
                for i in range(0, len(output) - 1):
                    frame[output[i][-1]] = output[i + 1][:-1]
                for k in frame:
                    if len(frame[k]) == 1:
                        frame[k] = frame[k][0]
                self.status_panel.speed.emit(f"{frame.get('time', '')}|{frame.get('speed', '').rstrip('x')}")
                self.status_panel.bitrate.emit(frame.get("bitrate", ""))
            except Exception:
                pass
        elif "remain" in msg:
            self.status_panel.nvencc_signal.emit(msg)
        self.append(msg)

    def blank(self, data):
        _, video_uuid, command_uuid = data.split(":")
        try:
            self.parent.current_video = self.main.find_video(video_uuid)
            self.current_command = self.main.find_command(self.parent.current_video, command_uuid)
        except FlixError:
            logger.error(f"Couldn't find video or command for UUID {video_uuid}:{command_uuid}")
            self.parent.current_video = None
            self.current_command = None
        self.setText("")
        self.parent.started_at = datetime.datetime.now(datetime.timezone.utc)

    def timer_update(self, cmd):
        self.parent.ticker_thread.state_signal.emit(cmd == "START")

    def closeEvent(self, event):
        self.hide()


class ElapsedTimeTicker(QtCore.QThread):
    state_signal = QtCore.Signal(bool)
    stop_signal = QtCore.Signal()  # Clean exit of program

    def __init__(self, parent, tick_signal):
        super().__init__(parent)
        self.parent = parent
        self.tick_signal = tick_signal

        self.send_tick_signal = False
        self.stop_received = False

        self.state_signal.connect(self.set_state)
        self.stop_signal.connect(self.on_stop)

    def __del__(self):
        self.wait()

    def run(self):
        while not self.stop_received:
            time.sleep(0.5)

            if not self.send_tick_signal:
                continue

            self.tick_signal.emit()

        logger.debug("Ticker thread stopped")

    def set_state(self, state):
        self.send_tick_signal = state

    def on_stop(self):
        self.stop_received = True


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
                self.parent.timer_signal.emit("START")
            elif msg == "STOP_TIMER":
                self.parent.timer_signal.emit("STOP")
            elif msg == "UPDATE_QUEUE":
                self.parent.status_panel.main.video_options.update_queue(currently_encoding=self.parent.converting)
            else:
                self.parent.log_signal.emit(msg)
