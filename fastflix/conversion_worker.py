# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty
from typing import Literal
from datetime import datetime

import reusables
from appdirs import user_data_dir
from pathvalidate import sanitize_filename

from fastflix.command_runner import BackgroundRunner
from fastflix.language import t


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".", 1)[0]


logger = logging.getLogger("fastflix-core")

log_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"


@reusables.log_exception(log="fastflix-core")
def queue_worker(gui_proc, worker_queue, status_queue, log_queue):
    runner = BackgroundRunner(log_queue=log_queue)
    gui_died = False
    currently_encoding = False
    video_uuid = None
    command_uuid = None
    command = None
    work_dir = None
    log_name = ""
    priority: Literal["Realtime", "High", "Above Normal", "Normal", "Below Normal", "Idle"] = "Normal"

    def start_command():
        nonlocal currently_encoding
        log_queue.put(f"CLEAR_WINDOW:{video_uuid}:{command_uuid}")
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            log_path / sanitize_filename(f"flix_conversion_{log_name[:64]}_{file_date()}.log"),
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        currently_encoding = True
        runner.start_exec(
            command,
            work_dir=work_dir,
        )
        runner.change_priority(priority)

    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            log_queue.put("STOP_TIMER")
            currently_encoding = False

            if runner.error_detected:
                logger.info(t("Error detected while converting"))

                status_queue.put(("error", video_uuid, command_uuid))
                if gui_died:
                    return
                continue

            status_queue.put(("complete", video_uuid, command_uuid))
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
            return
        else:
            if request[0] == "execute":
                _, video_uuid, command_uuid, command, work_dir, log_name = request
                start_command()

            if request[0] == "cancel":
                logger.debug(t("Cancel has been requested, killing encoding"))
                runner.kill()
                currently_encoding = False
                status_queue.put(("cancelled", video_uuid, command_uuid))
                log_queue.put("STOP_TIMER")

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

            if request[0] == "priority":
                priority = request[1]
                if runner.is_alive():
                    runner.change_priority(priority)
