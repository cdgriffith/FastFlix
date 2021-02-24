# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty
from typing import Optional
from multiprocessing import Manager, Lock

import reusables
from appdirs import user_data_dir
from box import Box
from pathvalidate import sanitize_filename

from fastflix.command_runner import BackgroundRunner
from fastflix.language import t
from fastflix.shared import file_date
from fastflix.models.queue import get_queue, save_queue
from fastflix.models.video import Video


logger = logging.getLogger("fastflix-core")

log_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"
after_done_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "after_done_logs"

queue_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.yaml"
queue_lock_file = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.lock"


CONTINUOUS = 0x80000000
SYSTEM_REQUIRED = 0x00000001


def prevent_sleep_mode():
    """https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx"""
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS | SYSTEM_REQUIRED)
        except Exception:
            logger.exception("Could not prevent system from possibly going to sleep during conversion")
        else:
            logger.debug("System has been asked to not sleep")


def allow_sleep_mode():
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS)
        except Exception:
            logger.exception("Could not allow system to resume sleep mode")
        else:
            logger.debug("System has been allowed to enter sleep mode again")


def get_next_video(queue_list, queue_lock) -> Optional[Video]:
    with queue_lock:
        for video in queue_list:
            if (
                not video.status.complete
                and not video.status.success
                and not video.status.cancelled
                and not video.status.error
                and not video.status.running
            ):
                logger.debug(f"Next video is {video.uuid} - {video.status}")
                return video.copy()


def set_status(
    current_video: Video,
    queue_list,
    queue_lock,
    complete=None,
    success=None,
    cancelled=None,
    errored=None,
    running=None,
    next_command=False,
    reset_commands=False,
):
    if not current_video:
        return

    with queue_lock:
        for i, video in enumerate(queue_list):
            if video.uuid == current_video.uuid:
                video_pos = i
                break
        else:
            logger.error(f"Can't find video {current_video.uuid} in queue to update its status: {queue_list}")
            return

        video_copy = queue_list.pop(video_pos)

        if complete is not None:
            video_copy.status.complete = complete
        if cancelled is not None:
            video_copy.status.cancelled = cancelled
        if errored is not None:
            video_copy.status.error = errored
        if success is not None:
            video_copy.status.success = success
        if running is not None:
            video_copy.status.running = running

        if complete or cancelled or errored or success:
            video_copy.status.running = False

        if next_command:
            video_copy.status.current_command += 1
        if reset_commands:
            video_copy.status.current_command = 0

        queue_list.insert(video_pos, video_copy)


@reusables.log_exception(log="fastflix-core")
def queue_worker(gui_proc, worker_queue, status_queue, log_queue, queue_list, queue_lock: Lock):
    runner = BackgroundRunner(log_queue=log_queue)

    # Command looks like (video_uuid, command_uuid, command, work_dir)
    after_done_command = ""
    gui_died = False
    currently_encoding = False
    paused = False
    video: Optional[Video] = None

    def start_command():
        nonlocal currently_encoding
        log_queue.put(
            f"CLEAR_WINDOW:{video.uuid}:{video.video_settings.conversion_commands[video.status.current_command].uuid}"
        )
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            log_path
            / sanitize_filename(
                f"flix_conversion_{video.video_settings.video_title or video.video_settings.output_path.stem}_{file_date()}.log"
            ),
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        prevent_sleep_mode()
        currently_encoding = True
        runner.start_exec(
            video.video_settings.conversion_commands[video.status.current_command].command,
            work_dir=str(video.work_path),
        )
        set_status(video, queue_list=queue_list, queue_lock=queue_lock, running=True)
        status_queue.put(("queue",))

        # status_queue.put(("running", commands_to_run[0][0], commands_to_run[0][1], runner.started_at.isoformat()))

    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            if runner.error_detected:
                logger.info(t("Error detected while converting"))

                # Stop working!
                currently_encoding = False
                set_status(video, queue_list=queue_list, queue_lock=queue_lock, errored=True)
                status_queue.put(("error",))
                allow_sleep_mode()
                if gui_died:
                    return
                continue

            # Successfully encoded, do next one if it exists
            # First check if the current video has more commands
            video.status.current_command += 1
            log_queue.put("STOP_TIMER")

            if len(video.video_settings.conversion_commands) > video.status.current_command:
                logger.debug("About to run next command for this video")
                set_status(video, queue_list=queue_list, queue_lock=queue_lock, next_command=True)
                status_queue.put(("queue",))
                start_command()
                continue
            else:
                logger.debug(f"{video.uuid} has been completed")
                set_status(video, queue_list=queue_list, queue_lock=queue_lock, next_command=True, complete=True)
                status_queue.put(("queue",))
                video = None

            if paused:
                currently_encoding = False
                allow_sleep_mode()
                logger.debug(t("Queue has been paused"))
                continue

            if video := get_next_video(queue_list=queue_list, queue_lock=queue_lock):
                start_command()
                continue
            else:
                currently_encoding = False
                allow_sleep_mode()
                logger.info(t("all conversions complete"))
                status_queue.put(("complete",))
                if after_done_command:
                    logger.info(f"{t('Running after done command:')} {after_done_command}")
                    try:
                        runner.start_exec(after_done_command, str(after_done_path))
                    except Exception:
                        logger.exception("Error occurred while running after done command")
                        continue
            if gui_died:
                return

        if not gui_died and not gui_proc.is_alive():
            gui_proc.join()
            gui_died = True
            if runner.is_alive() or currently_encoding:
                logger.info(t("The GUI might have died, but I'm going to keep converting!"))
            else:
                logger.debug(t("Conversion worker shutting down"))
                return

        try:
            request = worker_queue.get(block=True, timeout=0.05)
        except Empty:
            continue
        except KeyboardInterrupt:
            status_queue.put(("exit",))
            allow_sleep_mode()
            return
        else:
            if request[0] == "add_items":

                # Request looks like (queue command, log_dir, (commands))
                log_path = Path(request[1])
                if not currently_encoding and not paused:
                    video = get_next_video(queue_list=queue_list, queue_lock=queue_lock)
                    if video:
                        start_command()

            if request[0] == "cancel":
                logger.debug(t("Cancel has been requested, killing encoding"))
                runner.kill()
                if video:
                    set_status(video, queue_list=queue_list, queue_lock=queue_lock, reset_commands=True, cancelled=True)
                currently_encoding = False
                allow_sleep_mode()
                status_queue.put(("cancelled", video.uuid if video else ""))
                log_queue.put("STOP_TIMER")
                video = None

            if request[0] == "pause queue":
                logger.debug(t("Command worker received request to pause encoding after the current item completes"))
                paused = True

            if request[0] == "resume queue":
                paused = False
                logger.debug(t("Command worker received request to resume encoding"))
                if not currently_encoding:
                    if not video:
                        video = get_next_video(queue_list=queue_list, queue_lock=queue_lock)
                    start_command()

            if request[0] == "set after done":
                after_done_command = request[1]
                if after_done_command:
                    logger.debug(f'{t("Setting after done command to:")} {after_done_command}')
                else:
                    logger.debug(t("Removing after done command"))

            if request[0] == "pause encode":
                logger.debug(t("Command worker received request to pause current encode"))
                try:
                    runner.pause()
                except Exception:
                    logger.exception("Could not pause command")
                else:
                    status_queue.put(("paused encode",))
            if request[0] == "resume encode":
                logger.debug(t("Command worker received request to resume paused encode"))
                try:
                    runner.resume()
                except Exception:
                    logger.exception("Could not resume command")
                else:
                    status_queue.put(("resumed encode",))
