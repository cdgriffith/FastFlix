# -*- coding: utf-8 -*-
import logging
import sys
import traceback

# from multiprocessing import Process, Queue
from threading import Thread
from queue import Queue

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


def separate_app_process(fastflix):
    """ This prevents any QT components being imported in the main process"""
    from fastflix.application import start_app

    start_app(fastflix)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("fastflix-core")
    coloredlogs.install(level="DEBUG", logger=logger)
    logger.info(f"Starting FastFlix {__version__}")

    fastflix = FastFlix()
    fastflix.config = Config()

    fastflix.worker_queue = Queue()
    fastflix.status_queue = Queue()
    fastflix.log_queue = Queue()

    gui_proc = Thread(target=separate_app_process, args=(fastflix,))
    gui_proc.start()
    try:
        queue_worker(gui_proc, fastflix)
    finally:
        gui_proc.join()
