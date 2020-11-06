# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from queue import Empty, Queue

import reusables
from appdirs import user_data_dir

from fastflix.shared import allow_sleep_mode, file_date, prevent_sleep_mode
from fastflix.widgets.command_runner import BackgroundRunner
from fastflix.models.fastflix import FastFlix

# from multiprocessing


logger = logging.getLogger("fastflix-core")


def get_next_item(fastflix: FastFlix):
    for i, item in enumerate(fastflix.queue):
        if not item.status.complete and not item.status.running:
            return item


def queue_worker(fastflix: FastFlix):
    runner = BackgroundRunner(log_queue=fastflix.log_queue)

    def start_command(vid):
        fastflix.log_queue.put("CLEAR_WINDOW")
        reusables.remove_file_handlers(logger)
        new_file_handler = reusables.get_file_handler(
            fastflix.log_path / f"flix_conversion_{file_date()}.log",
            level=logging.DEBUG,
            log_format="%(asctime)s - %(message)s",
            encoding="utf-8",
        )
        logger.addHandler(new_file_handler)
        prevent_sleep_mode()
        runner.start_exec(
            vid.video_settings.conversion_commands[vid.status.current_command].command.replace("\\", "/"),
            work_dir=vid.work_path.name,
        )

    currently_encoding = False
    current_video = None
    while True:
        if currently_encoding and not runner.is_alive():
            reusables.remove_file_handlers(logger)
            if runner.error_detected:
                current_video.status.complete = True
                current_video.status.error = True
                current_video = None
                if fastflix.config.continue_on_failure:
                    # do next one
                    currently_encoding = False
                    continue
                else:
                    # Stop working!
                    currently_encoding = False
                    fastflix.status_queue.put("error")
                    allow_sleep_mode()
                    continue

            # Successfully encoded, do next one if it exists
            # First check if the current video has more commands
            logger.info("Command has completed")
            current_video.status.current_command += 1
            if (current_video.status.current_command + 1) <= len(current_video.video_settings.conversion_commands):
                logger.info("starting next command")
                start_command(current_video)
            else:
                logger.info("video complete")
                current_video.status.complete = True
                current_video.status.success = True
                current_video = get_next_item(fastflix)
                if current_video:
                    start_command(current_video)
                else:
                    logger.info("queue complete")
                    # Finished the queue
                    currently_encoding = False
                    fastflix.status_queue.put("complete")
                    allow_sleep_mode()
                    continue

        try:
            request = fastflix.worker_queue.get(block=True, timeout=0.05)
        except Empty:
            continue
        except KeyboardInterrupt:
            fastflix.status_queue.put("exit")
            allow_sleep_mode()
            return
        else:
            if request == "start" and not runner.is_alive():
                current_video = get_next_item(fastflix)
                start_command(current_video)
                currently_encoding = True
            if request == "cancel":
                runner.kill()
                index = 0
                allow_sleep_mode()
                fastflix.status_queue.put("cancelled")


def converter(gui_proc, fastflix):
    def log(msg, level=logging.INFO):
        fastflix.log_queue.put(msg)
        logger.log(level, msg)

    runner = BackgroundRunner(log_queue=fastflix.log_queue)

    # logger.info(f"Starting FastFlix {__version__}")

    # for leftover in Path(data_path).glob(f"encoder_output_*.log"):
    #     try:
    #         leftover.unlink()
    #     except OSError:
    #         pass

    sent_response = True
    gui_close_message = False
    queued_requests = []
    while True:
        if not gui_close_message and not gui_proc.is_alive():
            gui_proc.join()
            gui_close_message = True
            if runner.is_alive() or queued_requests:
                log("The GUI might have died, but I'm going to keep converting!", logging.WARNING)
            else:
                break
        try:
            request = fastflix.worker_queue.get(block=True, timeout=0.05)
        except Empty:
            if not runner.is_alive() and not sent_response and not queued_requests:
                ret = runner.process.poll()
                if ret > 0 or runner.error_detected:
                    log(f"Error during conversion", logging.WARNING)
                    fastflix.status_queue.put("error")
                else:
                    log("conversion complete")
                    fastflix.status_queue.put("complete")
                reusables.remove_file_handlers(logger)
                sent_response = True

                if not gui_proc.is_alive():
                    allow_sleep_mode()
                    return
        except KeyboardInterrupt:
            fastflix.status_queue.put("exit")
            allow_sleep_mode()
            return
        else:
            if request[0] == "command":
                if runner.is_alive():
                    queued_requests.append(request)
                else:
                    fastflix.log_queue.put("CLEAR_WINDOW")
                    reusables.remove_file_handlers(logger)
                    new_file_handler = reusables.get_file_handler(
                        fastflix.log_path / f"flix_conversion_{file_date()}.log",
                        level=logging.DEBUG,
                        log_format="%(asctime)s - %(message)s",
                        encoding="utf-8",
                    )
                    logger.addHandler(new_file_handler)
                    prevent_sleep_mode()
                    runner.start_exec(*request[1:])
                    sent_response = False
            if request[0] == "pause":
                runner.pause()
            if request[0] == "resume":
                runner.resume()
            if request[0] == "cancel":
                queued_requests = []
                runner.kill()
                allow_sleep_mode()
                fastflix.status_queue.put("cancelled")
                sent_response = True

        if not runner.is_alive():
            if queued_requests:
                runner.start_exec(*queued_requests.pop()[1:])
                sent_response = False
