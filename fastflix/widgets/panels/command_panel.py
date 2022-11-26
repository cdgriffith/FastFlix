#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import sys
from pathlib import Path

import reusables
from PySide6 import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.resources import get_icon


class Loop(QtWidgets.QGroupBox):
    def __init__(self, parent, condition, commands, number, name=""):
        super(Loop, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(f"Loop: {name}"))
        self.condition = condition
        self.number = number
        self.setStyleSheet("QGroupBox{padding-top:15px; margin-top:-18px}")

        for index, item in enumerate(commands, 1):
            new_item = Command(parent, item.command, index, item.name)
            layout.addWidget(new_item)
        self.setLayout(layout)


class Command(QtWidgets.QTabWidget):
    def __init__(self, parent, command, number, name="", enabled=True, height=None):
        super(Command, self).__init__(parent)
        self.command = command
        self.widget = QtWidgets.QTextBrowser()
        self.widget.setReadOnly(True)
        if not height:
            font_height = QtGui.QFontMetrics(self.widget.document().defaultFont()).height()
            lines = math.ceil(len(command) / 200)
            self.setMinimumHeight(int(font_height + ((lines + 2) * (font_height * 1.25))))
        else:
            self.setMinimumHeight(height)
        self.number = number
        self.name = name
        self.label = QtWidgets.QLabel(f"{t('Command')} {self.number}" if not self.name else self.name)
        self.update_grid()
        self.widget.setDisabled(not enabled)

    def update_grid(self):
        grid = QtWidgets.QVBoxLayout()
        self.label.setText(f"{t('Command')} {self.number}" if not self.name else self.name)
        grid.addWidget(self.label)
        grid.addWidget(self.widget)
        grid.addStretch()
        self.setLayout(grid)
        self.widget.setText(self.command)


class CommandList(QtWidgets.QWidget):
    def __init__(self, parent, app: FastFlixApp):
        super(CommandList, self).__init__(parent)
        self.app = app
        self.video_options = parent

        layout = QtWidgets.QGridLayout()

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel(t("Commands to execute")))

        copy_commands_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-copy", self.app.fastflix.config.theme)), t("Copy Commands")
        )
        copy_commands_button.setToolTip(t("Copy all commands to the clipboard"))
        copy_commands_button.clicked.connect(lambda: self.copy_commands_to_clipboard())

        save_commands_button = QtWidgets.QPushButton(
            QtGui.QIcon(get_icon("onyx-save", self.app.fastflix.config.theme)), t("Save Commands")
        )
        save_commands_button.setToolTip(t("Save commands to file"))
        save_commands_button.clicked.connect(lambda: self.save_commands_to_file())

        top_row.addStretch()

        top_row.addWidget(copy_commands_button)
        top_row.addWidget(save_commands_button)

        layout.addLayout(top_row, 0, 0)

        self.inner_widget = QtWidgets.QWidget()

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setMinimumHeight(200)

        layout.addWidget(self.scroll_area)
        self.commands = []
        self.setLayout(layout)

    def _prep_commands(self):
        commands = [x.command for x in self.commands if x.name != "hidden"]
        return f"\r\n".join(commands) if reusables.win_based else f"\n".join(commands)

    def copy_commands_to_clipboard(self):
        cmds = self._prep_commands()
        self.video_options.main.container.app.clipboard().setText(cmds)

    @reusables.log_exception("fastflix", show_traceback=False)
    def save_commands_to_file(self):
        ext = ".bat" if reusables.win_based else ".sh"
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, caption=t("Save Commands"), dir=str(Path("~").expanduser()), filter=f"{t('Save File')} (*{ext})"
        )
        if filename and filename[0]:
            Path(filename[0]).write_text(self._prep_commands())

    def update_commands(self, commands):
        self.inner_widget = QtWidgets.QWidget()
        sp = QtWidgets.QSizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        self.inner_widget.setSizePolicy(sp)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)
        self.commands = []
        for index, item in enumerate(commands, 1):
            if item.item == "command":
                new_item = Command(self.scroll_area, item.command, index, name=item.name)
                self.commands.append(item)
                layout.addWidget(new_item)
        layout.addStretch()
        self.inner_widget.setLayout(layout)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super(CommandList, self).resizeEvent(event)
