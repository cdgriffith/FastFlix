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
        for num, ext in file_numbers:
            if num not in self.temp_files:
                self.temp_files[num] = Path(self.tempdir.name, f'{uuid4().hex}.{ext}')
            command = command.replace(f'<tempfile.{num}.{ext}>', str(self.temp_files[num]))
        # TODO temp dirs
        return command

    @staticmethod
    def replace_loop_args(command, index, items):
        command = command.replace("<loop.index>", str(index))
        for i in range(len(items)):
            command = command.replace(f"<loop.{i}>", str(items[i]))
        return command

    def run_command(self, command):

        # if command:
        command = self.replace_temps(command)
        logger.info(f"Running command: {command}")
        self.process = self.start_exec(command)
        self.process.wait()
        # for line in self.process.stdout:
        #     logger.debug(f"command - {line}")
            # next_line = self.process.stdout.readline().decode('utf-8')
            # if not next_line:
            #     if self.process.poll() is not None:
            #         break
            #     else:
            #         continue
        return_code = self.process.poll()
        if self.killed:
            return self.app.cancelled.emit()
        return return_code
        # else:
        #     try:
        #         return target(**params)
        #     except Exception as err:
        #         logger.error(f'Could not run target {target}: {err}')

    def run(self):
        try:
            for command in self.command_list:
                if command.ensure_paths:
                    for path in command.ensure_paths:
                        path.mkdir(parents=True, exist_ok=True)
                if command.item == "command":
                    code = self.run_command(command.command)
                    print(code)
                    if code:
                        return self.app.completed.emit(str(code))
                elif command.item == "loop":
                    for index, res in enumerate(command.condition()):
                        for item in command.commands:
                            cmd = self.replace_loop_args(item.command, index, res)
                            code = self.run_command(cmd)
                            print(code)
                            if code:
                                return self.app.completed.emit(code)
        except:
            logger.exception("Could not run commands!")
            self.tempdir.cleanup()
            self.app.completed.emit(1)
        else:
            self.tempdir.cleanup()
            self.app.completed.emit(0)

    def start_exec(self, command):
        return Popen(command, shell=True, cwd=self.tempdir.name, stdin=PIPE, bufsize=0, universal_newlines=False)

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
