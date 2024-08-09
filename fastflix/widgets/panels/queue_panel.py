#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import sys
import logging
import os
from pathlib import Path

# import tracemalloc
import gc

from appdirs import user_data_dir
import reusables
from box import Box
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.models.video import Video
from fastflix.ff_queue import get_queue, save_queue
from fastflix.resources import get_icon, get_bool_env
from fastflix.shared import no_border, open_folder, yes_no_message, message, error_message
from fastflix.widgets.panels.abstract_list import FlixList
from fastflix.exceptions import FastFlixInternalException
from fastflix.windows_tools import allow_sleep_mode, prevent_sleep_mode
from fastflix.command_runner import BackgroundRunner

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

after_done_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "after_done_logs"


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

        settings = Box(copy.deepcopy(video.video_settings.model_dump()))
        # settings.output_path = str(settings.output_path)
        # for i, o in enumerate(video.attachment_tracks):
        #     if o.file_path:
        #         o["file_path"] = str(o["file_path"])
        # del settings.conversion_commands

        title.setToolTip(settings.video_encoder_settings.to_yaml())
        del settings

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
        grid.addWidget(
            QtWidgets.QLabel(f"{t('Audio Tracks')}: {len([1 for x in video.audio_tracks if x.enabled])}"), 0, 5
        )
        grid.addWidget(
            QtWidgets.QLabel(f"{t('Subtitles')}: {len([1 for x in video.subtitle_tracks if x.enabled])}"), 0, 6
        )
        grid.addWidget(QtWidgets.QLabel(status), 0, 7)
        if not video.status.error and video.status.complete and not get_bool_env("FF_DOCKERMODE"):
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

    def close(self) -> bool:
        for widget, item in self.widgets.items():
            item.close()
            self.widgets[widget] = None
        del self.video
        del self.widgets
        del self.parent
        gc.collect()
        return super().close()


class EncodingQueue(FlixList):
    def __init__(self, parent, app: FastFlixApp):
        self.main = parent.main
        self.app = app
        self.encode_paused = False
        self.encoding = False
        self.after_done_action = None
        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(QtWidgets.QLabel(t("Queue")))
        top_layout.addStretch(1)

        self.save_queue_button = QtWidgets.QPushButton(t("Save Queue"))
        self.save_queue_button.clicked.connect(self.manually_save_queue)
        self.save_queue_button.setFixedWidth(110)

        self.load_queue_button = QtWidgets.QPushButton(t("Load Queue"))
        self.load_queue_button.clicked.connect(self.manually_load_queue)
        self.load_queue_button.setFixedWidth(110)

        self.priority_widget = QtWidgets.QComboBox()
        self.priority_widget.addItems(["Realtime", "High", "Above Normal", "Normal", "Below Normal", "Idle"])
        self.priority_widget.setCurrentIndex(3)
        self.priority_widget.currentIndexChanged.connect(self.set_priority)

        self.clear_queue = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-clear-queue", self.app.fastflix.config.theme)), t("Clear Completed")
        )
        self.clear_queue.clicked.connect(self.clear_complete)
        self.clear_queue.setFixedWidth(150)
        self.clear_queue.setToolTip(t("Remove completed tasks"))

        self.pause_queue = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-pause", self.app.fastflix.config.theme)), t("Pause Queue")
        )
        self.pause_queue.clicked.connect(self.pause_resume_queue)
        # pause_queue.setFixedHeight(40)
        self.pause_queue.setFixedWidth(130)
        self.pause_queue.setToolTip(
            t("Wait for the current command to finish," " and stop the next command from processing")
        )

        self.pause_encode = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-pause", self.app.fastflix.config.theme)), t("Pause Encode")
        )
        self.pause_encode.clicked.connect(self.pause_resume_encode)
        # pause_queue.setFixedHeight(40)
        self.pause_encode.setFixedWidth(130)
        self.pause_encode.setToolTip(t("Pause / Resume the current command"))

        self.ignore_errors = QtWidgets.QCheckBox(t("Ignore Errors"))
        self.ignore_errors.toggled.connect(self.ignore_failures)
        self.ignore_errors.setFixedWidth(150)

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

        priority_label = QtWidgets.QLabel(t("Priority"))
        priority_label.setFixedWidth(55)

        top_layout.addWidget(self.load_queue_button, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.save_queue_button, QtCore.Qt.AlignRight)
        top_layout.addStretch(1)
        top_layout.addWidget(priority_label, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.priority_widget, QtCore.Qt.AlignRight)
        top_layout.addStretch(1)
        top_layout.addWidget(QtWidgets.QLabel(t("After Conversion")))
        top_layout.addWidget(self.after_done_combo, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.ignore_errors, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.pause_encode, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.pause_queue, QtCore.Qt.AlignRight)
        top_layout.addWidget(self.clear_queue, QtCore.Qt.AlignRight)

        super().__init__(app, parent, t("Queue"), "queue", top_row_layout=top_layout)
        try:
            self.queue_startup_check()
        except Exception:
            logger.exception("Could not load queue as it is outdated or malformed. Deleting for safety.")
            # with self.app.fastflix.queue_lock:
            #     save_queue([], queue_file=self.app.fastflix.queue_path, config=self.app.fastflix.config)

    def queue_startup_check(self, queue_file=None):
        new_queue = get_queue(queue_file or self.app.fastflix.queue_path)

        remove_vids = []
        for i, video in enumerate(new_queue):
            if video.status.complete:
                remove_vids.append(video)
            else:
                video.status.clear()

        for video in remove_vids:
            new_queue.remove(video)

        if queue_file:
            self.app.fastflix.conversion_list = new_queue
        elif new_queue:
            if yes_no_message(
                f"{t('Not all items in the queue were completed')}\n"
                f"{t('Would you like to keep them in the queue?')}",
                title="Recover Queue Items",
            ):
                self.app.fastflix.conversion_list = new_queue

        # registered_metadata = set()
        # for video in self.app.fastflix.conversion_list:
        #     if getattr(video.video_settings.video_encoder_settings, "hdr10plus_metadata", None):
        #         registered_metadata.add(Path(video.video_settings.video_encoder_settings.hdr10plus_metadata).name)
        #
        # for metadata_file in (self.app.fastflix.config.work_path / "queue_extras").glob("*.json"):
        #     if metadata_file.name not in registered_metadata:
        #         metadata_file.unlink(missing_ok=True)

        self.new_source()
        save_queue(self.app.fastflix.conversion_list, self.app.fastflix.queue_path, self.app.fastflix.config)

    def manually_save_queue(self):
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption=t("Save Queue"),
            dir=os.path.expanduser("~"),
            filter=f"FastFlix Queue File (*.yaml)",
        )
        if filename and filename[0]:
            save_queue(self.app.fastflix.conversion_list, filename[0], self.app.fastflix.config)
            message(t("Queue saved to") + f"{filename[0]}")

    def manually_load_queue(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, caption=t("Load Queue"), dir=os.path.expanduser("~"), filter=f"FastFlix Queue File (*.yaml)"
        )
        if filename and filename[0]:
            is_yes = True
            if self.app.fastflix.conversion_list:
                is_yes = yes_no_message(
                    (
                        t("This will remove all items in the queue currently")
                        + "\n"
                        + t(f"It will update it with the contents of")
                        + f":\n\n {filename[0]}\n\n"
                        + t("Are you sure you want to proceed?")
                    ),
                    title="Overwrite existing queue?",
                )
            filename = Path(filename[0])
            if not filename.exists():
                error_message(t("That file doesn't exist"))
            if is_yes:
                self.queue_startup_check(filename)

    def reorder(self, update=True):
        if self.app.fastflix.currently_encoding:
            # TODO error?
            logger.warning("Reorder queue called while encoding")
            return
        super().reorder(update=update)
        # TODO find better reorder method
        for i in range(len(self.tracks) - 1, -1, -1):
            del self.app.fastflix.conversion_list[i]

        self.app.fastflix.conversion_list = []
        for track in self.tracks:
            self.app.fastflix.conversion_list.append(track.video)

        for track in self.tracks:
            track.widgets.up_button.setDisabled(False)
            track.widgets.down_button.setDisabled(False)
        if self.tracks:
            self.tracks[0].widgets.up_button.setDisabled(True)
            self.tracks[-1].widgets.down_button.setDisabled(True)
        save_queue(self.app.fastflix.conversion_list, self.app.fastflix.queue_path, self.app.fastflix.config)

    def new_source(self):
        for i in range(len(self.tracks) - 1, -1, -1):
            self.tracks[i].close()
            del self.tracks[i]

        self.tracks = []

        for i, video in enumerate(self.app.fastflix.conversion_list, start=1):
            self.tracks.append(EncodeItem(self, video, index=i))
        if self.tracks:
            self.tracks[0].widgets.up_button.setDisabled(True)
            self.tracks[-1].widgets.down_button.setDisabled(True)
        super()._new_source(self.tracks)

        # snapshot = tracemalloc.take_snapshot()
        # top_stats = snapshot.statistics('lineno')
        #
        # print("[ Top 20 ]")
        # for stat in top_stats[:20]:
        #     print(stat)

    def clear_complete(self):
        for queued_item in self.tracks:
            if queued_item.video.status.complete:
                self.remove_item(queued_item.video, part_of_clear=True)
        self.new_source()

    def remove_item(self, video, part_of_clear=False):
        if self.app.fastflix.currently_encoding:
            # TODO error
            return

        for i, vid in enumerate(self.app.fastflix.conversion_list):
            if vid.uuid == video.uuid:
                pos = i
                break
        else:
            logger.error("No matching video found to remove from queue")
            return
        del self.app.fastflix.conversion_list[pos]

        if not part_of_clear:
            self.new_source()
        save_queue(self.app.fastflix.conversion_list, self.app.fastflix.queue_path, self.app.fastflix.config)

    def reload_from_queue(self, video):
        try:
            self.main.reload_video_from_queue(video)
        except FastFlixInternalException:
            pass
        else:
            self.remove_item(video)

    def reset_pause_encode(self):
        self.pause_encode.setText(t("Pause Encode"))
        self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        self.encode_paused = False

    def pause_resume_queue(self):
        if self.app.fastflix.conversion_paused:
            self.pause_queue.setText(t("Pause Queue"))
            self.pause_queue.setIcon(QtGui.QIcon(get_icon("onyx-pause", self.app.fastflix.config.theme)))
            send_next = self.main.send_next_video()
            logger.debug(f"queue resumed, will I send next? {send_next}")
        else:
            self.pause_queue.setText(t("Resume Queue"))
            self.pause_queue.setIcon(QtGui.QIcon(get_icon("play", self.app.fastflix.config.theme)))
            # self.app.fastflix.worker_queue.put(["pause queue"])
        self.app.fastflix.conversion_paused = not self.app.fastflix.conversion_paused

    def pause_resume_encode(self):
        if self.encode_paused:
            allow_sleep_mode()
            self.pause_encode.setText(t("Pause Encode"))
            self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
            self.app.fastflix.worker_queue.put(["resume encode"])
        else:
            if not yes_no_message(
                t("WARNING: This feature is not provided by the encoder software directly")
                + "<br><br>"
                + t("It is NOT supported by VCE or NVENC encoders, it will break the encoding")
                + "<br><br>"
                + t("Are you sure you want to continue?"),
                "Pause Warning",
            ):
                return
            prevent_sleep_mode()
            self.pause_encode.setText(t("Resume Encode"))
            self.pause_encode.setIcon(self.app.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.app.fastflix.worker_queue.put(["pause encode"])
        self.encode_paused = not self.encode_paused

    def ignore_failures(self):
        if self.ignore_errors.isChecked():
            self.app.fastflix.worker_queue.put(["ignore error"])
        else:
            self.app.fastflix.worker_queue.put(["stop on error"])

    @reusables.log_exception("fastflix", show_traceback=False)
    def set_after_done(self):
        option = self.after_done_combo.currentText()

        if option == "None":
            command = None
        elif option in self.app.fastflix.config.custom_after_run_scripts:
            command = self.app.fastflix.config.custom_after_run_scripts[option]
        elif reusables.win_based:
            command = done_actions["windows"][option]
        else:
            command = done_actions["linux"][option]

        self.after_done_action = command

    def retry_video(self, current_video):
        for i, video in enumerate(self.app.fastflix.conversion_list):
            if video.uuid == current_video.uuid:
                video.status.clear()
                break
        else:
            logger.error(f"Can't find video {current_video.uuid} in queue to update its status")
            return
        self.new_source()

    def move_up(self, widget):
        if not self.app.fastflix.currently_encoding:
            super().move_up(widget)

    def move_down(self, widget):
        if not self.app.fastflix.currently_encoding:
            super().move_down(widget)

    def add_to_queue(self):
        if not self.main.encoding_checks():
            return False

        if not self.main.build_commands():
            return False

        for video in self.app.fastflix.conversion_list:
            if video.status.complete:
                continue
            if self.app.fastflix.current_video.source == video.source:
                source_in_queue = True
            if self.app.fastflix.current_video.video_settings.output_path == video.video_settings.output_path:
                raise FastFlixInternalException(
                    f"{video.video_settings.output_path} {t('out file is already in queue')}"
                )

        # if source_in_queue:
        # TODO ask if ok
        # return

        self.app.fastflix.conversion_list.append(copy.deepcopy(self.app.fastflix.current_video))
        self.new_source()
        save_queue(self.app.fastflix.conversion_list, self.app.fastflix.queue_path, self.app.fastflix.config)

    def run_after_done(self):
        if not self.after_done_action:
            return
        logger.info(f"Running after done action: {self.after_done_action}")
        BackgroundRunner(self.app.fastflix.log_queue).start_exec(
            self.after_done_action, str(after_done_path), shell=True
        )

    def set_priority(self):
        self.app.fastflix.worker_queue.put(["priority", self.priority_widget.currentText()])
