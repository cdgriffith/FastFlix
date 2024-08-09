#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import secrets
import shlex
import time
from pathlib import Path
from subprocess import PIPE
from threading import Thread
from typing import Literal

from psutil import Popen

try:
    from psutil import (
        HIGH_PRIORITY_CLASS,
        REALTIME_PRIORITY_CLASS,
        IDLE_PRIORITY_CLASS,
        NORMAL_PRIORITY_CLASS,
        ABOVE_NORMAL_PRIORITY_CLASS,
        BELOW_NORMAL_PRIORITY_CLASS,
    )
except ImportError:
    priority_levels = {
        "Realtime": 20,
        "High": 10,
        "Above Normal": 5,
        "Normal": 0,
        "Below Normal": -10,
        "Idle": -20,
    }
else:
    priority_levels = {
        "Realtime": REALTIME_PRIORITY_CLASS,
        "High": HIGH_PRIORITY_CLASS,
        "Above Normal": ABOVE_NORMAL_PRIORITY_CLASS,
        "Normal": NORMAL_PRIORITY_CLASS,
        "Below Normal": BELOW_NORMAL_PRIORITY_CLASS,
        "Idle": IDLE_PRIORITY_CLASS,
    }

logger = logging.getLogger("fastflix-core")

__all__ = ["BackgroundRunner"]


class BackgroundRunner:
    def __init__(self, log_queue):
        self.process = None
        self.killed = False
        self.output_file = None
        self.error_output_file = None
        self.log_queue = log_queue
        self.error_detected = False
        self.success_detected = False
        self.error_message = []
        self.success_message = []
        self.started_at = None

    def start_exec(self, command, work_dir: str = None, shell: bool = False, errors=(), successes=()):
        self.clean()
        logger.debug(f"Using work dir: {work_dir}")
        work_path = Path(work_dir)
        work_path.mkdir(exist_ok=True, parents=True)
        self.output_file = work_path / f"encoder_output_{secrets.token_hex(6)}.log"
        self.error_output_file = work_path / f"encoder_error_output_{secrets.token_hex(6)}.log"
        logger.debug(f"command output file set to: {self.output_file}")
        logger.debug(f"command error output file set to: {self.error_output_file}")
        self.output_file.touch(exist_ok=True)
        self.error_output_file.touch(exist_ok=True)
        self.error_message = errors
        self.success_message = successes
        logger.info(f"Running command: {command}")
        try:
            self.process = Popen(
                shlex.split(command.replace("\\", "\\\\")) if not shell and isinstance(command, str) else command,
                shell=shell,
                cwd=work_dir,
                stdout=open(self.output_file, "w"),
                stderr=open(self.error_output_file, "w"),
                stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc on linux
                encoding="utf-8",
            )
        except PermissionError:
            logger.error(
                "Could not encode video due to permissions error."
                "Please make sure encoder is executable and you have permissions to run it."
                "Otherwise try running FastFlix as an administrator."
            )
            self.error_detected = True
            return
        except Exception:
            logger.exception("Could not start worker process")
            self.error_detected = True
            return

        self.started_at = datetime.datetime.now(datetime.timezone.utc)

        Thread(target=self.read_output).start()

    def change_priority(
        self, new_priority: Literal["Realtime", "High", "Above Normal", "Normal", "Below Normal", "Idle"]
    ):
        try:
            if self.process:
                self.process.nice(priority_levels[new_priority])
                logger.info(f"Set command priority to {new_priority}")
        except Exception:
            logger.exception(f"Could not set process priority to {new_priority}")

    def read_output(self):
        with (
            open(self.output_file, "r", encoding="utf-8", errors="ignore") as out_file,
            open(self.error_output_file, "r", encoding="utf-8", errors="ignore") as err_file,
        ):
            while True:
                time.sleep(0.01)
                if not self.is_alive():
                    excess = out_file.read()
                    logger.info(excess)
                    self.log_queue.put(excess)

                    err_excess = err_file.read()
                    logger.info(err_excess)
                    self.log_queue.put(err_excess)
                    if self.process.returncode is not None and self.process.returncode > 0:
                        self.error_detected = True
                    break
                line = out_file.readline().rstrip()
                if line:
                    logger.info(line)
                    self.log_queue.put(line)
                    if not self.success_detected:
                        for success in self.success_message:
                            if success in line:
                                self.success_detected = True

                err_line = err_file.readline().rstrip()
                if err_line:
                    logger.info(err_line)
                    self.log_queue.put(err_line)
                    if "Conversion failed!" in err_line or "Error during output" in err_line:
                        self.error_detected = True
                    if not self.error_detected:
                        for error in self.error_message:
                            if error in err_line:
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

    def clean(self):
        self.kill(log=False)
        self.process = None
        self.error_detected = False
        self.success_detected = False
        self.killed = False
        self.started_at = None

    def kill(self, log=True):
        if self.process and self.process.poll() is None:
            if log:
                logger.info(f"Killing worker process {self.process.pid}")
            try:
                # if reusables.win_based:
                #     os.kill(self.process.pid, signal.CTRL_C_EVENT)
                # else:
                #     os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.terminate()
                self.process.kill()
            except Exception as err:
                if log:
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
