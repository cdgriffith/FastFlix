# -*- coding: utf-8 -*-
import logging
import sys
import traceback

from multiprocessing import Process, Queue

# from threading import Thread
# from queue import Queue

try:
    import coloredlogs
    import requests
    import reusables
    from appdirs import user_data_dir
    from box import Box

    from fastflix.conversion_worker import queue_worker
    from fastflix.models.config import Config
    from fastflix.models.fastflix import FastFlix
    from fastflix.program_downloads import ask_for_ffmpeg, latest_ffmpeg
    from fastflix.shared import (
        allow_sleep_mode,
        base_path,
        error_message,
        file_date,
        latest_fastflix,
        message,
        prevent_sleep_mode,
    )
    from fastflix.version import __version__

except ImportError as err:
    traceback.print_exc()
    print("Could not load FastFlix properly!", file=sys.stderr)
    input("Please report this issue on https://github.com/cdgriffith/FastFlix/issues (press any key to exit)")
    sys.exit(1)


def separate_app_process(worker_queue, status_queue, log_queue):
    """ This prevents any QT components being imported in the main process"""
    from fastflix.application import start_app

    start_app(worker_queue, status_queue, log_queue)


def main():
    logger = logging.getLogger("fastflix-core")
    logger.addHandler(reusables.get_stream_handler(level=logging.DEBUG))
    logger.setLevel(logging.DEBUG)
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    worker_queue = Queue()
    status_queue = Queue()
    log_queue = Queue()

    gui_proc = Process(
        target=separate_app_process,
        args=(
            worker_queue,
            status_queue,
            log_queue,
        ),
    )
    gui_proc.start()
    try:
        queue_worker(worker_queue, status_queue, log_queue)
    finally:
        gui_proc.join()
