#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
import secrets
import shlex
from pathlib import Path
from subprocess import PIPE, Popen
from threading import Thread
import psutil

logger = logging.getLogger("fastflix-core")

__all__ = ["BackgroundRunner"]

white_detect = re.compile(r"^\s+")


class BackgroundRunner:
    def __init__(self, log_queue):
        self.process = None
        self.killed = False
        self.output_file = None
        self.error_output_file = None
        self.log_queue = log_queue
        self.error_detected = False

    def start_exec(self, command, work_dir, shell=False):
        logger.info(f"Running command: {command}")
        Path(work_dir).mkdir(exist_ok=True, parents=True)
        self.output_file = Path(work_dir) / f"encoder_output_{secrets.token_hex(6)}.log"
        self.error_output_file = Path(work_dir) / f"encoder_error_output_{secrets.token_hex(6)}.log"
        self.process = psutil.Popen(
            shlex.split(command) if not shell else command,
            shell=shell,
            cwd=work_dir,
            stdout=open(self.output_file, "w"),
            stderr=open(self.error_output_file, "w"),
            stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc on linux
            encoding="utf-8",
        )
        self.error_detected = False

        Thread(target=self.read_output).start()

    def read_output(self):
        with open(self.output_file, "r", encoding="utf-8") as out_file, open(
            self.error_output_file, "r", encoding="utf-8"
        ) as err_file:
            while True:
                if not self.is_alive():
                    excess = out_file.read()
                    logger.info(excess)
                    self.log_queue.put(excess)

                    err_excess = err_file.read()
                    logger.info(err_excess)
                    self.log_queue.put(err_excess)
                    break
                line = out_file.readline().rstrip()
                if line:
                    logger.info(line)
                    self.log_queue.put(line)

                err_line = err_file.readline().rstrip()
                if err_line:
                    logger.info(err_line)
                    self.log_queue.put(err_line)
                    if "Conversion failed!" in err_line:
                        self.error_detected = True
        try:
            self.output_file.unlink()
            self.error_output_file.unlink()
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

    def pause(self):
        if not self.process:
            return False
        self.process.suspend()

    def resume(self):
        if not self.process:
            return False
        self.process.resume()
