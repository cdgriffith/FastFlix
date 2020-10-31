# -*- coding: utf-8 -*-
from multiprocessing import Process, Queue
import logging

import coloredlogs

from fastflix.models.fastflix import FastFlix
from fastflix.models.config import Config
from fastflix.conversion_worker import converter
from fastflix.application import start_app
from fastflix.version import __version__


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

    gui_proc = Process(target=start_app, args=(fastflix,))
    gui_proc.start()
    converter(gui_proc, fastflix)
