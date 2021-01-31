# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty

import reusables
from appdirs import user_data_dir
from filelock import FileLock
from box import Box

from fastflix.command_runner import BackgroundRunner
from fastflix.language import t
from fastflix.shared import file_date
from fastflix.models.queue import STATUS, REQUEST, Queue

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


@reusables.log_exception(log="fastflix-core")
def queue_worker(gui_proc, worker_queue, status_queue, log_queue):
    runner = BackgroundRunner(log_queue=log_queue)

    # Command looks like (video_uuid, command_uuid, command, work_dir)
    after_done_command = ""
    commands_to_run = []
    gui_died = False
    currently_encoding = False
    paused = False

    def start_command():
        nonlocal currently_encoding
        log_queue.put(f"CLEAR_WINDOW:{commands_to_run[0][0]}:{commands_to_run[0][1]}")
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            log_path / f"flix_conversion_{commands_to_run[0][4]}_{file_date()}.log",
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        prevent_sleep_mode()
        currently_encoding = True
        runner.start_exec(
            commands_to_run[0][2],
            work_dir=commands_to_run[0][3],
        )

        status_queue.put(("running", commands_to_run[0][0], commands_to_run[0][1], runner.started_at.isoformat()))

    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            if runner.error_detected:
                logger.info(t("Error detected while converting"))

                # Stop working!
                currently_encoding = False
                status_queue.put(("error", commands_to_run[0][0], commands_to_run[0][1]))
                commands_to_run = []
                allow_sleep_mode()
                if gui_died:
                    return
                continue

            # Successfully encoded, do next one if it exists
            # First check if the current video has more commands
            logger.info(t("Command has completed"))
            status_queue.put(("converted", commands_to_run[0][0], commands_to_run[0][1]))
            commands_to_run.pop(0)
            if commands_to_run:
                if not paused:
                    logger.info(t("starting next command"))
                    start_command()
                else:
                    currently_encoding = False
                    allow_sleep_mode()
                    logger.debug(t("Queue has been paused"))
                continue
            else:
                logger.info(t("all conversions complete"))
                # Finished the queue
                # fastflix.current_encoding = None
                currently_encoding = False
                status_queue.put(("complete",))
                allow_sleep_mode()
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
                for command in request[2]:
                    if command not in commands_to_run:
                        logger.debug(t(f"Adding command to the queue for {command[4]} - {command[2]}"))
                        commands_to_run.append(command)
                    # else:
                    #     logger.debug(t(f"Command already in queue: {command[1]}"))
                if not runner.is_alive() and not paused:
                    logger.debug(t("No encoding is currently in process, starting encode"))
                    start_command()
            if request[0] == "cancel":
                logger.debug(t("Cancel has been requested, killing encoding"))
                runner.kill()
                currently_encoding = False
                allow_sleep_mode()
                status_queue.put(("cancelled", commands_to_run[0][0], commands_to_run[0][1]))
                commands_to_run = []
            if request[0] == "pause queue":
                logger.debug(t("Command worker received request to pause encoding after the current item completes"))
                paused = True
            if request[0] == "resume queue":
                paused = False
                logger.debug(t("Command worker received request to resume encoding"))
                if commands_to_run and not runner.is_alive():
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
                    status_queue.put(("paused encode", commands_to_run[0][0], commands_to_run[0][1]))
            if request[0] == "resume encode":
                logger.debug(t("Command worker received request to resume paused encode"))
                try:
                    runner.resume()
                except Exception:
                    logger.exception("Could not resume command")
                else:
                    status_queue.put(("resumed encode", commands_to_run[0][0], commands_to_run[0][1]))
