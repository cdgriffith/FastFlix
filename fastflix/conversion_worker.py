# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty
from typing import Optional
from multiprocessing import Lock

import reusables
from appdirs import user_data_dir
from pathvalidate import sanitize_filename

from fastflix.command_runner import BackgroundRunner
from fastflix.language import t
from fastflix.shared import file_date
from fastflix.models.video import Video
from fastflix.ff_queue import save_queue


logger = logging.getLogger("fastflix-core")

log_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"
after_done_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "after_done_logs"

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


@reusables.log_exception(log="fastflix-core")
def queue_worker(gui_proc, worker_queue, status_queue, log_queue):
    runner = BackgroundRunner(log_queue=log_queue)
    after_done_command = ""
    gui_died = False
    currently_encoding = False
    video_uuid = None
    command_uuid = None
    command = None
    work_dir = None
    log_name = ""

    def start_command():
        nonlocal currently_encoding
        log_queue.put(f"CLEAR_WINDOW:{video_uuid}:{command_uuid}")
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            log_path / sanitize_filename(f"flix_conversion_{log_name}_{file_date()}.log"),
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        prevent_sleep_mode()
        currently_encoding = True
        runner.start_exec(
            command,
            work_dir=work_dir,
        )

    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            log_queue.put("STOP_TIMER")
            allow_sleep_mode()
            currently_encoding = False

            if runner.error_detected:
                logger.info(t("Error detected while converting"))

                status_queue.put(("error", video_uuid, command_uuid))
                if gui_died:
                    return
                continue

            status_queue.put(("complete", video_uuid, command_uuid))
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
            if request[0] == "execute":
                _, video_uuid, command_uuid, command, work_dir, log_name = request
                start_command()

            if request[0] == "cancel":
                logger.debug(t("Cancel has been requested, killing encoding"))
                runner.kill()
                currently_encoding = False
                allow_sleep_mode()
                status_queue.put(("cancelled", video_uuid, command_uuid))
                log_queue.put("STOP_TIMER")
                video = None

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

            if request[0] == "resume encode":
                logger.debug(t("Command worker received request to resume paused encode"))
                try:
                    runner.resume()
                except Exception:
                    logger.exception("Could not resume command")
