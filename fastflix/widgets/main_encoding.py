#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import logging
from collections import namedtuple
from pathlib import Path
from queue import Empty
from typing import TYPE_CHECKING, Optional

import reusables
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException, FlixError
from fastflix.language import t
from fastflix.models.video import Video
from fastflix.resources import get_icon
from fastflix.shared import error_message, message, yes_no_message
from fastflix.ui_constants import ICONS
from fastflix.ui_scale import scaler
from fastflix.widgets.status_bar import STATE_COMPLETE, STATE_ENCODING, STATE_ERROR, STATE_IDLE
from fastflix.windows_tools import allow_sleep_mode, prevent_sleep_mode

if TYPE_CHECKING:
    from fastflix.widgets.main import Main

logger = logging.getLogger("fastflix")

Request = namedtuple(
    "Request",
    ["request", "video_uuid", "command_uuid", "command", "work_dir", "log_name", "shell"],
    defaults=[None, None, None, None, None, False],
)

Response = namedtuple("Response", ["status", "video_uuid", "command_uuid"])


class Notifier(QtCore.QThread):
    def __init__(self, parent, app, status_queue):
        super().__init__(parent)
        self.app = app
        self.main: Main = parent
        self.status_queue = status_queue
        self._shutdown = False

    def request_shutdown(self):
        """Request graceful shutdown of the thread."""
        self._shutdown = True

    def run(self):
        while not self._shutdown:
            # Message looks like (command, video_uuid, command_uuid)
            try:
                status = self.status_queue.get(timeout=0.5)
            except Empty:
                continue
            self.app.processEvents()
            if status[0] == "exit":
                logger.debug("GUI received ask to exit")
                self.main.close_event.emit()
                return
            self.main.status_update_signal.emit(status)
            self.app.processEvents()


class EncodingMixin:
    """Mixin for Main: encoding orchestration, queue dispatch, and worker communication."""

    self: Main

    def encoding_checks(self):
        if not self.input_video:
            error_message(t("Have to select a video first"))
            return False
        if not self.output_video:
            error_message(t("Please specify output video"))
            return False
        try:
            if self.input_video.resolve().absolute() == Path(self.output_video).resolve().absolute():
                error_message(t("Output video path is same as source!"))
                return False
        except OSError:
            # file system may not support resolving
            pass

        out_file_path = Path(self.output_video)
        if out_file_path.exists() and out_file_path.stat().st_size > 0:
            sm = QtWidgets.QMessageBox()
            sm.setText("That output file already exists and is not empty!")
            sm.addButton("Cancel", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Overwrite", QtWidgets.QMessageBox.RejectRole)
            sm.exec()
            if sm.clickedButton().text() == "Cancel":
                return False
        return True

    def set_convert_button(self):
        if not self.app.fastflix.currently_encoding:
            self.widgets.convert_button.setText(f"{t('Convert')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(get_icon("play-round", self.app.fastflix.config.theme)))
            self.widgets.convert_button.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))
        else:
            self.widgets.convert_button.setText(f"{t('Cancel')}  ")
            self.widgets.convert_button.setIcon(QtGui.QIcon(get_icon("black-x", self.app.fastflix.config.theme)))
            self.widgets.convert_button.setIconSize(scaler.scale_size(ICONS.MEDIUM, ICONS.MEDIUM))

    @reusables.log_exception("fastflix", show_traceback=True)
    def encode_video(self):
        if self.app.fastflix.currently_encoding:
            sure = yes_no_message(t("Are you sure you want to stop the current encode?"), title="Confirm Stop Encode")
            if not sure:
                return
            logger.info(t("Canceling current encode"))
            self.app.fastflix.worker_queue.put(["cancel"])
            self.video_options.queue.reset_pause_encode()
            return

        if self.app.fastflix.conversion_paused:
            return error_message("Queue is currently paused")

        if self.app.fastflix.current_video:
            add_current = True
            if self.app.fastflix.conversion_list and self.app.fastflix.current_video:
                add_current = yes_no_message("Add current video to queue?", yes_text="Yes", no_text="No")
            if add_current:
                if not self.add_to_queue():
                    return

        for video in self.app.fastflix.conversion_list:
            if video.status.ready:
                video_to_send: Video = video
                break
        else:
            error_message(t("There are no videos to start converting"))
            return

        logger.debug(t("Starting conversion process"))

        self.app.fastflix.currently_encoding = True
        prevent_sleep_mode()
        self.set_convert_button()
        self.send_video_request_to_worker_queue(video_to_send)
        self.disable_all()
        self.video_options.show_status()
        video_name = video_to_send.video_settings.video_title or video_to_send.video_settings.output_path.stem
        self.encoding_status_signal.emit(f"{t('Encoding')}: {video_name}", STATE_ENCODING)
        self.encoding_progress_signal.emit(0)

    def add_to_queue(self):
        try:
            code = self.video_options.queue.add_to_queue()
        except FastFlixInternalException as err:
            error_message(str(err))
            return
        else:
            if code is not None:
                return code
        self.video_options.show_queue()

        self.clear_current_video()
        return True

    def conversion_complete(self, success: bool):
        self.paused = False
        allow_sleep_mode()
        self.set_convert_button()

        if not success:
            self.encoding_status_signal.emit(t("Encoding error"), STATE_ERROR)
            if self.app.fastflix.config.show_error_message:
                error_message(t("There was an error during conversion and the queue has stopped"), title=t("Error"))
            self.video_options.queue.new_source()
        else:
            self.encoding_status_signal.emit(t("All conversions complete"), STATE_COMPLETE)
            self.video_options.show_queue()
            if self.app.fastflix.config.show_complete_message:
                message(t("All queue items have completed"), title=t("Success"))

    def conversion_cancelled(self, video: Video):
        self.set_convert_button()

        exists = video.video_settings.output_path.exists()

        if exists:
            sm = QtWidgets.QMessageBox()
            sm.setWindowTitle(t("Cancelled"))
            sm.setText(f"{t('Conversion cancelled, delete incomplete file')}\n{video.video_settings.output_path}?")
            sm.addButton(t("Delete"), QtWidgets.QMessageBox.YesRole)
            sm.addButton(t("Keep"), QtWidgets.QMessageBox.NoRole)
            sm.exec()
            if sm.clickedButton().text() == t("Delete"):
                try:
                    video.video_settings.output_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def status_update(self, status_response):
        response = Response(*status_response)
        logger.debug(f"Updating queue from command worker: {response}")

        video_to_send: Optional[Video] = None
        errored = False
        same_video = False

        for video in self.app.fastflix.conversion_list:
            if response.video_uuid == video.uuid:
                video.status.running = False

                if response.status == "cancelled":
                    video.status.cancelled = True
                    self.encoding_status_signal.emit(t("Encoding cancelled"), STATE_IDLE)
                    self.encoding_progress_signal.emit(0)
                    self.end_encoding()
                    self.conversion_cancelled(video)
                    self.video_options.update_queue()
                    return

                if response.status == "complete":
                    video.status.current_command += 1
                    if len(video.video_settings.conversion_commands) > video.status.current_command:
                        same_video = True
                        video_to_send = video
                        break
                    else:
                        video.status.complete = True
                        self._post_encode_process(video)

                if response.status == "error":
                    video.status.error = True
                    errored = True
                    if self.app.fastflix.config.enable_history:
                        try:
                            self._record_history(video, success=False)
                        except Exception:
                            logger.exception("Failed to record history entry for errored encode")
                break

        if errored and not self.video_options.queue.ignore_errors.isChecked():
            self.end_encoding()
            self.conversion_complete(success=False)
            return

        if not video_to_send:
            for video in self.app.fastflix.conversion_list:
                if video.status.ready:
                    video_to_send = video
                    break

        if not video_to_send:
            self.end_encoding()
            self.conversion_complete(success=True)
            return

        self.app.fastflix.currently_encoding = True
        if not same_video and self.app.fastflix.conversion_paused:
            return self.end_encoding()

        self.send_video_request_to_worker_queue(video_to_send)

    def end_encoding(self):
        self.app.fastflix.currently_encoding = False
        allow_sleep_mode()
        self.video_options.queue.run_after_done()
        self.video_options.update_queue()
        self.set_convert_button()
        self.encoding_progress_signal.emit(0)

    def send_next_video(self) -> bool:
        if not self.app.fastflix.currently_encoding:
            for video in self.app.fastflix.conversion_list:
                if video.status.ready:
                    video.status.running = True
                    self.send_video_request_to_worker_queue(video)
                    self.app.fastflix.currently_encoding = True
                    prevent_sleep_mode()
                    self.set_convert_button()
                    return True
        self.app.fastflix.currently_encoding = False
        allow_sleep_mode()
        self.set_convert_button()
        return False

    def send_video_request_to_worker_queue(self, video: Video):
        command = video.video_settings.conversion_commands[video.status.current_command]
        self.app.fastflix.currently_encoding = True
        prevent_sleep_mode()
        if video.status.current_command == 0:
            video.status.encode_started_at = datetime.datetime.now(datetime.timezone.utc)

        self.app.fastflix.worker_queue.put(
            Request(
                request="execute",
                video_uuid=video.uuid,
                command_uuid=command.uuid,
                command=command.command,
                work_dir=str(video.work_path),
                log_name=video.video_settings.video_title or video.video_settings.output_path.stem,
                shell=command.shell,
            )
        )
        video.status.running = True
        self.video_options.update_queue()
        video_name = video.video_settings.video_title or video.video_settings.output_path.stem
        self.encoding_status_signal.emit(f"{t('Encoding')}: {video_name}", STATE_ENCODING)

    def find_video(self, uuid) -> Video:
        for video in self.app.fastflix.conversion_list:
            if uuid == video.uuid:
                return video
        raise FlixError(f"{t('No video found for')} {uuid}")

    def find_command(self, video: Video, uuid) -> int:
        for i, command in enumerate(video.video_settings.conversion_commands, start=1):
            if uuid == command.uuid:
                return i
        raise FlixError(f"{t('No command found for')} {uuid}")
