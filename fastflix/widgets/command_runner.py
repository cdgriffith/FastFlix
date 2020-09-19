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
import secrets

import reusables

from qtpy import QtCore, QtWidgets, QtGui

logger = logging.getLogger("fastflix")

__all__ = ["CommandRunner"]

white_detect = re.compile(r"^\s+")


class CommandRunner(QtCore.QThread):
    def __init__(self, parent, command_list, work_dir):
        super().__init__(parent)
        self.tempdir = str(Path(work_dir) / f"temp_{secrets.token_hex(12)}")
        os.makedirs(self.tempdir, exist_ok=True)
        self.app = parent
        self.command_list = command_list
        self.process = None
        self.killed = False
        self.re_tempfile = re.compile(r"<tempfile\.(\d+)\.(\w+)>")
        self.re_tempdir = re.compile(r"<tempdir\.(\d+)>")
        self.temp_files = {}
        self.temp_dirs = {}

    def replace_temps(self, command):
        file_numbers = set(self.re_tempfile.findall(command))
        for num, ext in file_numbers:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir, f"{uuid4().hex}.{ext}")
            command = command.replace(f"<tempfile.{num}.{ext}>", str(self.temp_files[num]))
        for num in set(self.re_tempdir.findall(command)):
            if num not in self.temp_dirs:
                self.temp_dirs[num] = Path(tempfile.mkdtemp(prefix=f"{num}_", dir=self.tempdir))
            command = command.replace(f"<tempdir.{num}>", str(self.temp_dirs[num]))
        return command

    def loop_creates(self, dirs, files):
        for num, ext in files:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir, f"{uuid4().hex}.{ext}")
        for num in dirs:
            if num not in self.temp_dirs:
                self.temp_dirs[num] = Path(tempfile.mkdtemp(prefix=f"{num}_", dir=self.tempdir))

    @staticmethod
    def replace_loop_args(command, index, items):
        command = command.replace("<loop.index>", str(index))
        for i in range(len(items)):
            command = command.replace(f"<loop.{i}>", str(items[i]))
        return command

    def run_command(self, command, command_type=None):
        command = self.replace_temps(command)
        logger.info(f"Running command: {command}")
        self.process = self.start_exec(command)
        if not command_type:
            line_wait = False
            line = ""
            while True:
                char = self.process.stdout.read(1)
                if char == "" and self.process.poll() is not None:
                    logger.info(line)
                    break
                if char != "":
                    if char in ("\r", "\n"):
                        logger.info(line)
                        line = ""
                        continue
                    if ord(char) == 8:
                        if not line_wait:
                            logger.info(line)
                            line = ""
                        line_wait = True
                        continue
                    if line_wait and -ord(char) == 32:
                        continue
                    line += char
                    line_wait = False

        elif command_type == "ffmpeg":
            last_write = 0
            for i, line in enumerate(self.process.stdout):
                if self.killed:
                    logger.info(line.rstrip())
                    break
                if not white_detect.match(line):
                    if "Skipping NAL unit" in line:
                        last_write -= 1
                        continue

                    line = line.strip()
                    if line.startswith("frame"):
                        if last_write + 50 < i:
                            last_write = i
                            logger.info(line.rstrip())
                    else:
                        logger.info(line.rstrip())
                    if line.startswith(("frame", "encoded")):
                        self.app.log_label_update(line.strip())

        return_code = self.process.poll()
        return return_code

    def run(self):
        try:
            for command in self.command_list:
                if self.killed:
                    return
                if command.ensure_paths:
                    for path in command.ensure_paths:
                        path.mkdir(parents=True, exist_ok=True)
                if command.item == "command":
                    code = self.run_command(command.command, command.exe)
                    if code and not self.killed:
                        return self.app.completed.emit(str(code))
                elif command.item == "loop":
                    self.loop_creates(command.dirs, command.files)
                    for index, res in enumerate(command.condition(self.temp_files, self.temp_dirs)):
                        for item in command.commands:
                            cmd = self.replace_loop_args(item.command, index, res)
                            code = self.run_command(cmd, item.exe)
                            if code and not self.killed:
                                return self.app.completed.emit(str(code))
        except Exception as err:
            logger.exception(f"Could not run commands - {err}")
            if not self.killed:
                self.app.completed.emit(1)
        else:
            if not self.killed:
                self.app.completed.emit(0)

    def start_exec(self, command):
        return Popen(command, shell=True, cwd=self.tempdir, stdout=PIPE, stderr=STDOUT, encoding="utf-8")

    def is_alive(self):
        if not self.process:
            return False
        return True if self.process.poll() is None else False

    def kill(self):
        logger.info(f"Killing worker process {self.process.pid}")
        if self.process:
            try:
                self.process.terminate()
            except Exception as err:
                logger.exception(f"Couldn't terminate process: {err}")
        self.killed = True
        self.app.cancelled.emit()
