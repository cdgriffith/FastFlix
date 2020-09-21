#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
import secrets
import shlex
from pathlib import Path
from subprocess import STDOUT, Popen
from threading import Thread

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
        self.output_file = Path(work_dir) / f"encoder_output_{secrets.token_hex(6)}.log"
        self.process = Popen(
            shlex.split(command), cwd=work_dir, stdout=open(self.output_file, "w"), stderr=STDOUT, encoding="utf-8"
        )
        Thread(target=self.read_output).start()

    def read_output(self):
        with open(self.output_file, "r") as f:
            while True:
                if not self.is_alive():
                    excess = f.read()
                    logger.info(excess)
                    self.log_queue.put(excess)
                    break
                line = f.readline().rstrip()
                if line:
                    logger.info(line)
                    self.log_queue.put(line)
        try:
            self.output_file.unlink()
        except OSError:
            pass

    def read(self, limit=None):
        if not self.is_alive():
            return
        return self.process.stdout.read(limit)

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
                self.process.kill()
            except Exception as err:
                logger.exception(f"Couldn't terminate process: {err}")
        self.killed = True
