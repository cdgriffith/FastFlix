#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
import tempfile
from pathlib import Path
from uuid import uuid4
from subprocess import Popen, PIPE, STDOUT
import os
import signal
from threading import Thread

import reusables


logger = logging.getLogger("fastflix-core")

__all__ = ["BackgroundRunner"]

white_detect = re.compile(r"^\s+")


class BackgroundRunner:
    def __init__(self, log_queue):
        self.process = None
        self.killed = False
        self.log_queue = log_queue

    def start_exec(self, command, work_dir):
        logger.info(f"Running command: {command}")
        self.process = Popen(
            command,
            shell=True,
            cwd=work_dir,
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
            encoding="utf-8",
            preexec_fn=os.setsid if not reusables.win_based else None,
        )
        Thread(target=self.read_output).start()

    def read_output(self):
        while True:
            if not self.is_alive():
                return
            line = self.process.stdout.readline().rstrip()
            if line:
                logger.info(line)
                self.log_queue.put(line)

    def read(self, limit=None):
        if not self.is_alive():
            return
        return self.process.stdout.read(limit)

    # def run_command(self, command, work_dir):
    #     logger.info(f"Running command: {command}")
    #     last_write = 0
    #     for i, line in enumerate(self.process.stdout):
    #         if self.killed:
    #             logger.info(line.rstrip())
    #             break
    #         if not white_detect.match(line):
    #             if "Skipping NAL unit" in line:
    #                 last_write -= 1
    #                 continue
    #
    #             line = line.strip()
    #             if line.startswith("frame"):
    #                 if last_write + 50 < i:
    #                     last_write = i
    #                     logger.info(line.rstrip())
    #             else:
    #                 logger.info(line.rstrip())
    #
    #     return_code = self.process.poll()
    #     return return_code

    def is_alive(self):
        if not self.process:
            return False
        return True if self.process.poll() is None else False

    def kill(self):
        logger.info(f"Killing worker process {self.process.pid}")
        if self.process:
            try:
                # if reusables.win_based:
                #     os.kill(self.process.pid, signal.CTRL_C_EVENT)
                # else:
                #     os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.terminate()
            except Exception as err:
                logger.exception(f"Couldn't terminate process: {err}")
        self.killed = True
