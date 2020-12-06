#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import re
import secrets
import shlex
from pathlib import Path
from subprocess import PIPE
from threading import Thread

from psutil import Popen

logger = logging.getLogger("fastflix-core")

__all__ = ["BackgroundRunner"]

white_detect = re.compile(r"^\s+")


class BackgroundRunner:
    def __init__(self, log_queue):
        self.process = None
        self.process_two = None
        self.killed = False
        self.output_file = None
        self.error_output_file = None
        self.log_queue = log_queue
        self.error_detected = False
        self.success_detected = False
        self.error_message = []
        self.success_message = []

    def start_exec(self, command, work_dir: str = None, shell: bool = False, errors=(), successes=()):
        self.clean()
        logger.info(f"Running command: {command}")
        Path(work_dir).mkdir(exist_ok=True, parents=True)
        self.output_file = Path(work_dir) / f"encoder_output_{secrets.token_hex(6)}.log"
        self.error_output_file = Path(work_dir) / f"encoder_error_output_{secrets.token_hex(6)}.log"
        self.output_file.touch(exist_ok=True)
        self.error_output_file.touch(exist_ok=True)
        self.error_message = errors
        self.success_message = successes

        self.process = Popen(
            shlex.split(command) if not shell and isinstance(command, str) else command,
            shell=shell,
            cwd=work_dir,
            stdout=open(self.output_file, "w"),
            stderr=open(self.error_output_file, "w"),
            stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc on linux
            encoding="utf-8",
        )

        Thread(target=self.read_output).start()

    def start_piped_exec(self, command_one, command_two, work_dir, errors=(), successes=()):
        self.clean()
        logger.info(f"Running commands: {' '.join(command_one)} | {' '.join(command_two)}")
        Path(work_dir).mkdir(exist_ok=True, parents=True)
        self.output_file = Path(work_dir) / f"encoder_output_{secrets.token_hex(6)}.log"
        self.error_output_file = Path(work_dir) / f"encoder_error_output_{secrets.token_hex(6)}.log"
        self.output_file.touch(exist_ok=True)
        self.error_output_file.touch(exist_ok=True)
        self.error_message = errors
        self.success_message = successes

        self.process = Popen(
            command_one,
            cwd=work_dir,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,  # FFmpeg can try to read stdin and wrecks havoc on linux
        )

        self.process_two = Popen(
            command_two,
            cwd=work_dir,
            stdout=open(self.output_file, "w"),
            stderr=open(self.error_output_file, "w"),
            stdin=self.process.stdout,
            encoding="utf-8",
        )

        self.error_detected = False

        Thread(target=self.read_output).start()

    def read_output(self):
        with open(self.output_file, "r", encoding="utf-8", errors="ignore") as out_file, open(
            self.error_output_file, "r", encoding="utf-8", errors="ignore"
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
                    if not self.success_detected:
                        for success in self.success_message:
                            if success in line:
                                self.success_detected = True

                err_line = err_file.readline().rstrip()
                if err_line:
                    logger.info(err_line)
                    self.log_queue.put(err_line)
                    if "Conversion failed!" in err_line:
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
        if self.process_two:
            # TODO make sure process 1 dies cleanly
            return True if self.process_two.poll() is None else False
        return True if self.process.poll() is None else False

    def clean(self):
        self.kill(log=False)
        self.process = None
        self.process_two = None
        self.error_detected = False
        self.success_detected = False
        self.killed = False

    def kill(self, log=True):
        if self.process_two:
            if log:
                logger.info(f"Killing worker process {self.process_two.pid}")
            try:
                self.process_two.terminate()
                self.process_two.kill()
            except Exception as err:
                if log:
                    logger.exception(f"Couldn't terminate process: {err}")
        if self.process:
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
        if self.process_two:
            return False
        if not self.process:
            return False
        self.process.suspend()

    def resume(self):
        if self.process_two:
            return False
        if not self.process:
            return False
        self.process.resume()


# if __name__ == "__main__":
#     from queue import Queue
#
#     logging.basicConfig(level=logging.DEBUG)
#     br = BackgroundRunner(Queue())
#     import shutil
#
#     ffmpeg = shutil.which("ffmpeg")
#     br.start_piped_exec(
#         command_one=shlex.split(
#             rf'"{ffmpeg}" -loglevel panic -i C:\\Users\\Chris\\scoob_short.mkv -c:v copy -vbsf hevc_mp4toannexb -f hevc -'
#         ),
#         command_two=shlex.split(r'"C:\\Users\\Chris\\ffmpeg\\hdr10plus_parser.exe" --verify -'),
#         work_dir=r"C:\Users\Chris",
#     )
# import time
# time.sleep(1)
# br.read_output()
