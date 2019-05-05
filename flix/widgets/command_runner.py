#!/usr/bin/env python
import logging
import re
import time
import tempfile
from pathlib import Path
from uuid import uuid4
from subprocess import Popen, PIPE, run, STDOUT
import sys

import reusables

from flix.shared import QtCore, QtWidgets, QtGui

logger = logging.getLogger('flix')

__all__ = ['Worker']

white_detect = re.compile(r'^\s+')


class Worker(QtCore.QThread):
    def __init__(self, parent, command_list, work_dir):
        super(Worker, self).__init__(parent)
        self.tempdir = tempfile.TemporaryDirectory(prefix="temp_", dir=work_dir)
        # self.logger = logging.getLogger(f'command_logger')
        # TODO setup file logger for command output self.logger
        # TODO calculate time based off frames
        self.app = parent
        self.command_list = command_list
        self.process = None
        self.killed = False
        self.re_tempfile = re.compile(r'<tempfile\.(\d+)\.(\w+)>')
        self.re_tempdir = re.compile(r'<tempdir\.(\d+)>')
        self.temp_files = {}
        self.temp_dirs = {}

    def replace_temps(self, command):
        file_numbers = set(self.re_tempfile.findall(command))
        for num, ext in file_numbers:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir.name, f'{uuid4().hex}.{ext}')
            command = command.replace(f'<tempfile.{num}.{ext}>', str(self.temp_files[num]))
        for num in set(self.re_tempdir.findall(command)):
            if num not in self.temp_dirs:
                self.temp_dirs[num] = Path(tempfile.mkdtemp(prefix=f"{num}_", dir=self.tempdir.name))
            command = command.replace(f'<tempdir.{num}>', str(self.temp_dirs[num]))
        return command

    def loop_creates(self, dirs, files):
        for num, ext in files:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir.name, f'{uuid4().hex}.{ext}')
        for num in dirs:
            if num not in self.temp_dirs:
                self.temp_dirs[num] = Path(tempfile.mkdtemp(prefix=f"{num}_", dir=self.tempdir.name))

    @staticmethod
    def replace_loop_args(command, index, items):
        command = command.replace("<loop.index>", str(index))
        for i in range(len(items)):
            command = command.replace(f"<loop.{i}>", str(items[i]))
        return command

    def run_command(self, command, command_type=None):

        # if command:
        command = self.replace_temps(command)
        logger.info(f"Running command: {command}")
        self.process = self.start_exec(command)
        if not command_type:
            line_wait = False
            line = ''
            while True:
                char = self.process.stdout.read(1)
                if char == '' and self.process.poll() is not None:
                    logger.info(line)
                    break
                if char != '':
                    if char in ('\r', '\n'):
                        logger.info(line)
                        line = ''
                        continue
                    if ord(char) == 8:
                        if not line_wait:
                            logger.info(line)
                            line = ''
                        line_wait = True
                        continue
                    if line_wait and -ord(char) == 32:
                        continue
                    line += char
                    line_wait = False

                    # simple print to console
                    # sys.stdout.write(char if 32 < ord(char) < 126 else f"[{ord(char)}]")
                    # sys.stdout.flush()
                    # lineAfterCarriage += char
                    # if char in ('\r', '\n'):

            # for line in self.process.stdout:
            #     if self.killed:
            #         break
            #     logger.info(line.strip())
        elif command_type == 'ffmpeg':
            for line in self.process.stdout:
                if self.killed:
                    logger.info(line.rstrip())
                    break
                if not white_detect.match(line):
                    logger.info(line.rstrip())

        # self.process.wait()
        # for line in self.process.stdout:
        #     logger.debug(f"command - {line}")
        # next_line = self.process.stdout.readline().decode('utf-8')
        # if not next_line:
        #     if self.process.poll() is not None:
        #         break
        #     else:
        #         continue
        return_code = self.process.poll()
        return return_code
        # else:
        #     try:
        #         return target(**params)
        #     except Exception as err:
        #         logger.error(f'Could not run target {target}: {err}')

    def run(self):
        try:
            for command in self.command_list:
                if self.killed:
                    self.tempdir.cleanup()
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
            self.tempdir.cleanup()
            if not self.killed:
                self.app.completed.emit(1)
        else:
            self.tempdir.cleanup()
            if not self.killed:
                self.app.completed.emit(0)

    def start_exec(self, command):
        return Popen(command, shell=True, cwd=self.tempdir.name, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                     universal_newlines=True)

    def is_alive(self):
        if not self.process:
            return False
        return True if self.process.poll() is None else False

    def kill(self):
        self.killed = True
        logger.info("Killing worker process")
        if self.process and self.is_alive():
            if reusables.win_based:
                run(f"TASKKILL /F /PID {self.process.pid} /T", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
            else:
                run(f"kill -9 {self.process.pid}", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
            try:
                self.process.terminate()
            except Exception as err:
                print(f"Couldn't kill process: {err}")
        self.app.cancelled.emit()
        self.exit()
