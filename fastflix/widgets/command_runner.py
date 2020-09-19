#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import re
import secrets
import shlex
import signal
import tempfile
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from threading import Thread
from uuid import uuid4

import reusables

logger = logging.getLogger("fastflix-core")

__all__ = ["BackgroundRunner"]

white_detect = re.compile(r"^\s+")


class BackgroundRunner:
    def __init__(self, log_queue):
        self.process = None
        self.killed = False
        self.output_file = None
        self.log_queue = log_queue

    def start_exec(self, command, work_dir):
        logger.info(f"Running command: {command}")
        self.clean()
        self.output_file = Path(work_dir) / f"encoder_output_{secrets.token_hex(6)}.log"
        self.process = Popen(
            command, shell=True, cwd=work_dir, stdout=open(self.output_file, "w"), stderr=STDOUT, encoding="utf-8"
        )
        Thread(target=self.read_output).start()

    def read_output(self):
        with open(self.output_file, "r") as f:
            while True:
                if not self.is_alive():
                    excess = f.read()
                    logger.info(excess)
                    self.log_queue.put(excess)
                    return
                line = f.readline().rstrip()
                if line:
                    logger.info(line)
                    self.log_queue.put(line)

    def read(self, limit=None):
        if not self.is_alive():
            return
        return self.process.stdout.read(limit)

    def clean(self):
        if self.output_file and self.output_file.exists():
            try:
                self.output_file.unlink()
            except OSError:
                pass

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
