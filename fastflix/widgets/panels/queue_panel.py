#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import sys
import logging

import reusables
from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.ff_queue import get_queue, save_queue
from fastflix.resources import get_icon, get_bool_env
from fastflix.shared import no_border, open_folder, yes_no_message
from fastflix.widgets.panels.abstract_list import FlixList

logger = logging.getLogger("fastflix")

done_actions = {
    "linux": {
        "shutdown": 'shutdown -h 1 "FastFlix conversion complete, shutting down"',
        "restart": 'shutdown -r 1 "FastFlix conversion complete, rebooting"',
        "logout": "logout",
        "sleep": "pm-suspend",
        "hibernate": "pm-hibernate",
    },
    "windows": {
        "shutdown": "shutdown /s",
        "restart": "shutdown /r",
        "logout": "shutdown /l",
        "hibernate": "shutdown /h",
    },
}


class EncodeItem(QtWidgets.QTabWidget):
    def __init__(self, parent, video: Video, index, first=False):
        self.loading = True
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.first = first
        self.last = False
        self.video = video.copy()
        self.setFixedHeight(60)

        self.widgets = Box(
            up_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("up-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            down_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("down-arrow", self.parent.app.fastflix.config.theme)), ""
            ),
            cancel_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("black-x", self.parent.app.fastflix.config.theme)), ""
            ),
            reload_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("edit-box", self.parent.app.fastflix.config.theme)), ""
            ),
            retry_button=QtWidgets.QPushButton(
                QtGui.QIcon(get_icon("undo", self.parent.app.fastflix.config.theme)), ""
            ),
        )

        for widget in self.widgets.values():
            widget.setStyleSheet(no_border)

        title = QtWidgets.QLabel(
            video.video_settings.video_title
            if video.video_settings.video_title
            else video.video_settings.output_path.name
        )
        title.setFixedWidth(300)

        settings = Box(copy.deepcopy(video.video_settings.dict()))
        settings.output_path = str(settings.output_path)
        for i, o in enumerate(settings.attachment_tracks):
            if o.get("file_path"):
                o["file_path"] = str(o["file_path"])
        del settings.conversion_commands

        title.setToolTip(settings.to_yaml())

        open_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("play", self.parent.app.fastflix.config.theme)), t("Open Directory")
        )
        open_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        open_button.setIconSize(QtCore.QSize(14, 14))
        open_button.clicked.connect(lambda: open_folder(video.video_settings.output_path.parent))

        view_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("play", self.parent.app.fastflix.config.theme)), t("Watch")
        )
        view_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        view_button.setIconSize(QtCore.QSize(14, 14))
        view_button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(video.video_settings.output_path)))
        )

        open_button.setStyleSheet(no_border)
        view_button.setStyleSheet(no_border)

        add_retry = False
        status = t("Ready to encode")
        if video.status.error:
            status = t("Encoding errored")
        elif video.status.complete:
            status = f"{t('Encoding complete')}"
        elif video.status.running:
            status = (
                f"{t('Encoding command')} {video.status.current_command + 1} {t('of')} "
                f"{len(video.video_settings.conversion_commands)}"
            )
        elif video.status.cancelled:
            status = t("Cancelled")
            add_retry = True

        if not self.video.status.running:
            self.widgets.cancel_button.clicked.connect(lambda: self.parent.remove_item(self.video))
            self.widgets.reload_button.clicked.connect(lambda: self.parent.reload_from_queue(self.video))
            self.widgets.cancel_button.setFixedWidth(25)
            self.widgets.reload_button.setFixedWidth(25)
        else:
            self.widgets.cancel_button.hide()
            self.widgets.reload_button.hide()

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        # grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(title, 0, 1, 1, 3)
        grid.addWidget(QtWidgets.QLabel(f"{video.video_settings.video_encoder_settings.name}"), 0, 4)
        grid.addWidget(QtWidgets.QLabel(f"{t('Audio Tracks')}: {len(video.video_settings.audio_tracks)}"), 0, 5)
        grid.addWidget(QtWidgets.QLabel(f"{t('Subtitles')}: {len(video.video_settings.subtitle_tracks)}"), 0, 6)
        grid.addWidget(QtWidgets.QLabel(status), 0, 7)
        if video.status.complete and not get_bool_env("FF_DOCKERMODE"):
            grid.addWidget(view_button, 0, 8)
            grid.addWidget(open_button, 0, 9)
        elif add_retry:
            grid.addWidget(self.widgets.retry_button, 0, 8)
            self.widgets.retry_button.setFixedWidth(25)
            self.widgets.retry_button.clicked.connect(lambda: self.parent.retry_video(self.video))

        right_buttons = QtWidgets.QHBoxLayout()
        right_buttons.addWidget(self.widgets.reload_button)
        right_buttons.addWidget(self.widgets.cancel_button)

        grid.addLayout(right_buttons, 0, 10, alignment=QtCore.Qt.AlignRight)

        self.setLayout(grid)
        self.loading = False
        self.updating_burn = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        self.widgets.down_button.setFixedWidth(20)
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def set_first(self, first=True):
        self.first = first

    def set_last(self, last=True):
        self.last = last

    def set_outdex(self, outdex):
        pass

    @property
    def enabled(self):
        return True

    def update_enable(self):
        pass

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update(build_thumbnail=False)


class EncodingQueue(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        self.main = parent.main
        self.app = app
        self.paused = False
        self.encode_paused = False
        self.encoding = False
        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(QtWidgets.QLabel(t("Queue")))
        top_layout.addStretch(1)

        self.clear_queue = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-clear-queue", self.app.fastflix.config.theme)), t("Clear Completed")
        )
        self.clear_queue.clicked.connect(self.clear_complete)
        self.clear_queue.setFixedWidth(120)
        self.clear_queue.setToolTip(t("Remove completed tasks"))

        self.pause_queue = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-pause", self.app.fastflix.config.theme)), t("Pause Queue")
        )
        self.pause_queue.clicked.connect(self.pause_resume_queue)
        # pause_queue.setFixedHeight(40)
        self.pause_queue.setFixedWidth(120)
        self.pause_queue.setToolTip(
            t("Wait for the current command to finish," " and stop the next command from processing")
        )

        self.pause_encode = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-pause", self.app.fastflix.config.theme)), t("Pause Encode")
        )
        self.pause_encode.clicked.connect(self.pause_resume_encode)
        # pause_queue.setFixedHeight(40)
        self.pause_encode.setFixedWidth(120)
        self.pause_encode.setToolTip(t("Pause / Resume the current command"))

        self.after_done_combo = QtWidgets.QComboBox()
        self.after_done_combo.addItem("None")
        actions = set()
        if reusables.win_based:
            actions.update(done_actions["windows"].keys())

        elif sys.platform == "darwin":
            actions.update(["shutdown", "restart"])
        else:
            actions.update(done_actions["linux"].keys())
        if self.app.fastflix.config.custom_after_run_scripts:
            actions.update(self.app.fastflix.config.custom_after_run_scripts)

        self.after_done_combo.addItems(sorted(actions))
        self.after_done_combo.setToolTip("Run a command after conversion completes")
        self.after_done_combo.currentIndexChanged.connect(lambda: self.set_after_done())
        self.after_done_combo.setMaximumWidth(150)
        top_layout.addWidget(QtWidgets.QLabel(t("After Conversion")))
        top_layout.addWidget(self.after_done_combo, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.pause_encode, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.pause_queue, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.clear_queue, QtCore.Qt.AlignRight)

        super().__init__(app, parent, t("Queue"), "queue", top_row_layout=top_layout)
        try:
            self.queue_startup_check()
        except Exception:
            logger.exception("Could not load queue as it is outdated or malformed. Deleting for safety.")
            with self.app.fastflix.queue_lock:
                save_queue([], queue_file=self.app.fastflix.queue_path, config=self.app.fastflix.config)

    def queue_startup_check(self):
        new_queue = get_queue(self.app.fastflix.queue_path, self.app.fastflix.config)
        # self.app.fastflix.queue.append(item)
        reset_vids = []
        remove_vids = []
        for i, video in enumerate(new_queue):
            if video.status.running:
                reset_vids.append(i)
            if video.status.complete:
                remove_vids.append(video)

        for index in reset_vids:
            vid: Video = new_queue.pop(index)
            vid.status.clear()
            new_queue.insert(index, vid)

        for video in remove_vids:
            new_queue.remove(video)

        if new_queue:
            if yes_no_message(
                f"{t('Not all items in the queue were completed')}\n"
                f"{t('Would you like to keep them in the queue?')}",
                title="Recover Queue Items",
            ):
                with self.app.fastflix.queue_lock:
                    for item in new_queue:
                        self.app.fastflix.queue.append(item)
                    # self.app.fastflix.queue = []
            with self.app.fastflix.queue_lock:
                save_queue(self.app.fastflix.queue, self.app.fastflix.queue_path, self.app.fastflix.config)
            self.new_source()

    def reorder(self, update=True):
        super().reorder(update=update)

        with self.app.fastflix.queue_lock:
            for i in range(len(self.app.fastflix.queue)):
                self.app.fastflix.queue.pop()
            for track in self.tracks:
                self.app.fastflix.queue.append(track.video)

        for track in self.tracks:
            track.widgets.up_button.setDisabled(False)
            track.widgets.down_button.setDisabled(False)
        if self.tracks:
            self.tracks[0].widgets.up_button.setDisabled(True)
            self.tracks[-1].widgets.down_button.setDisabled(True)

    def new_source(self):
        for track in self.tracks:
            track.close()
        self.tracks = []
        for i, video in enumerate(self.app.fastflix.queue, start=1):
            self.tracks.append(EncodeItem(self, video, index=i))
        if self.tracks:
            self.tracks[0].widgets.up_button.setDisabled(True)
            self.tracks[-1].widgets.down_button.setDisabled(True)
        super()._new_source(self.tracks)

    def clear_complete(self):
        for queued_item in self.tracks:
            if queued_item.video.status.complete:
                self.remove_item(queued_item.video, part_of_clear=True)
        with self.app.fastflix.queue_lock:
            save_queue(self.app.fastflix.queue, self.app.fastflix.queue_path, self.app.fastflix.config)
        self.new_source()

    def remove_item(self, video, part_of_clear=False):
        with self.app.fastflix.queue_lock:
            for i, vid in enumerate(self.app.fastflix.queue):
                if vid.uuid == video.uuid:
                    pos = i
                    break
            else:
                logger.error("No matching video found to remove from queue")
                return
            self.app.fastflix.queue.pop(pos)
            if not part_of_clear:
                save_queue(self.app.fastflix.queue, self.app.fastflix.queue_path, self.app.fastflix.config)
        if not part_of_clear:
            self.new_source()

    def reload_from_queue(self, video):
        self.main.reload_video_from_queue(video)
        self.remove_item(video)

    def reset_pause_encode(self):
        self.pause_encode.setText(t("Pause Encode"))
        self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        self.encode_paused = False

    def pause_resume_queue(self):
        if self.paused:
            self.pause_queue.setText(t("Pause Queue"))
            self.pause_queue.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
            for i, video in enumerate(self.app.fastflix.queue):
                if video.status.ready:
                    self.main.converting = True
                    self.main.set_convert_button(False)
                    break
            self.app.fastflix.worker_queue.put(["resume queue"])
        else:
            self.pause_queue.setText(t("Resume Queue"))
            self.pause_queue.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.app.fastflix.worker_queue.put(["pause queue"])
        self.paused = not self.paused

    def pause_resume_encode(self):
        if self.encode_paused:
            self.pause_encode.setText(t("Pause Encode"))
            self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
            self.app.fastflix.worker_queue.put(["resume encode"])
        else:
            self.pause_encode.setText(t("Resume Encode"))
            self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.app.fastflix.worker_queue.put(["pause encode"])
        self.encode_paused = not self.encode_paused

    @reusables.log_exception("fastflix", show_traceback=False)
    def set_after_done(self):
        option = self.after_done_combo.currentText()

        if option == "None":
            command = ""
        elif option in self.app.fastflix.config.custom_after_run_scripts:
            command = self.app.fastflix.config.custom_after_run_scripts[option]
        elif reusables.win_based:
            command = done_actions["windows"][option]
        else:
            command = done_actions["linux"][option]

        self.app.fastflix.worker_queue.put(["set after done", command])

    def retry_video(self, current_video):
        with self.app.fastflix.queue_lock:
            for i, video in enumerate(self.app.fastflix.queue):
                if video.uuid == current_video.uuid:
                    video_pos = i
                    break
            else:
                logger.error(f"Can't find video {current_video.uuid} in queue to update its status")
                return

            video = self.app.fastflix.queue.pop(video_pos)
            video.status.cancelled = False
            video.status.current_command = 0

            self.app.fastflix.queue.insert(video_pos, video)
            save_queue(self.app.fastflix.queue, self.app.fastflix.queue_path, self.app.fastflix.config)

        self.new_source()
