#!/usr/bin/env python
import logging
import re
import tempfile
from pathlib import Path
from uuid import uuid4
from subprocess import Popen, PIPE, run, STDOUT

import reusables

from flix.shared import QtCore

logger = logging.getLogger('flix')

__all__ = ['Worker']


class Worker(QtCore.QThread):
    def __init__(self, parent, command_list, work_dir):
        super(Worker, self).__init__(parent)
        self.tempdir = tempfile.TemporaryDirectory(prefix="Temp", dir=work_dir)
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
        print(file_numbers)
        for num, ext in file_numbers:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir.name, f'{uuid4().hex}.{ext}')
            print(num)
            command = command.replace(f'<tempfile.{num}.{ext}>', str(self.temp_files[num]))
            print(command)
        # TODO temp dirs
        return command

    def run_command(self, command=None, target=None, params=None):

        if command:
            print(command)
            command = self.replace_temps(command)
            print(command)
            logger.info(f"Running command: {command}")
            self.process = self.start_exec(command)
            while True:
                next_line = self.process.stdout.readline().decode('utf-8')
                if not next_line:
                    if self.process.poll() is not None:
                        break
                    else:
                        continue
                logger.debug(f"ffmpeg - {next_line}")
            return_code = self.process.poll()
            if self.killed:
                return self.app.cancelled.emit()
        else:
            try:
                return_code = target(**params)
            except Exception as err:
                logger.error(f'Could not run target {target}: {err}')
                #return self.app.completed.emit(1)

    def run(self):
        current_group = 0
        command_groups = {}
        # for command in self.command_list:
        #     if not command.loop:
        #         current_group += 1
        #         command_groups[current_group] = command
        #         continue
        #     if current_group in command_groups:
        #         command_groups[current_group].append(command)
        #     else:
        #         command_groups[current_group] = command
        #
        # for command_set in command_groups:
        #     if isinstance(command_set, list):
        #         for command in command_set:
        #             self.run_command(command)
        #     else:
        #         self.run_command(command_set)

        for command in self.command_list:
            self.run_command(command.command)
        self.tempdir.cleanup()
        self.app.completed.emit(0)

    def start_exec(self, command):
        return Popen(command, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True, cwd=self.tempdir.name)

    def is_alive(self):
        if not self.process:
            return False
        return True if self.process.poll() is None else False

    def kill(self):
        if self.process and self.is_alive():
            self.killed = True
            if reusables.win_based:
                run(f"TASKKILL /F /PID {self.process.pid} /T", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            else:
                run(f"kill -9 {self.process.pid}", stdin=PIPE, stdout=PIPE, stderr=PIPE)
            return self.process.terminate()

    def __del__(self):
        self.kill()
