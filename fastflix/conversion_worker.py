# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty

import reusables
from appdirs import user_data_dir

from fastflix.command_runner import BackgroundRunner
from fastflix.language import t
from fastflix.shared import allow_sleep_mode, file_date, prevent_sleep_mode

logger = logging.getLogger("fastflix-core")


# def get_next_item(fastflix: FastFlix):
#     for i, item in enumerate(fastflix.queue):
#         if not item.status.complete and not item.status.running:
#             return item


def queue_worker(gui_proc, worker_queue, status_queue, log_queue):
    runner = BackgroundRunner(log_queue=log_queue)

    # Command looks like (video_uuid, command_uuid, command, work_dir)

    commands_to_run = []
    gui_died = False
    currently_encoding = False
    log_path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"

    def start_command():
        nonlocal currently_encoding
        log_queue.put(f"CLEAR_WINDOW:{commands_to_run[0][0]}:{commands_to_run[0][1]}")
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            log_path / f"flix_conversion_{file_date()}.log",
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        prevent_sleep_mode()
        currently_encoding = True
        status_queue.put(("running", commands_to_run[0][0], commands_to_run[0][1]))
        runner.start_exec(
            commands_to_run[0][2],
            work_dir=commands_to_run[0][3],
        )

    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            if runner.error_detected:
                logger.info(t("Error detected while converting"))
                # if fastflix.config.continue_on_failure:
                #     # do next one
                #     currently_encoding = False
                #     continue
                # else:

                # Stop working!
                currently_encoding = False
                status_queue.put(("error", commands_to_run[0][0], commands_to_run[0][1]))
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
                logger.info(t("starting next command"))
                start_command()
            else:
                logger.info(t("all conversions complete"))
                # Finished the queue
                # fastflix.current_encoding = None
                currently_encoding = False
                status_queue.put(("complete",))
                allow_sleep_mode()

            if gui_died:
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
            # Request looks like (queue command, log_dir, (commands))
            # TODO don't open "view new" dialog if not single video
            # TODO disable queue window change when converting
            if request[0] == "add_items":
                log_path = Path(request[1])
                commands_to_run.extend(request[2])
                if not runner.is_alive():
                    start_command()
            if request[0] == "cancel":
                runner.kill()
                allow_sleep_mode()
                status_queue.put(("cancelled", commands_to_run[0][0], commands_to_run[0][1]))
                commands_to_run = []
                currently_encoding = False

        if not gui_died and not gui_proc.is_alive():
            gui_proc.join()
            gui_died = True
            if runner.is_alive() or currently_encoding:
                logger.info(t("The GUI might have died, but I'm going to keep converting!"))
            else:
                break
