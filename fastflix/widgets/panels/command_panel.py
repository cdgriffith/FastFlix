#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
from pathlib import Path

import reusables
from qtpy import QtCore, QtGui, QtWidgets


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
    def __init__(self, parent, command, number, name="", enabled=True):
        super(Command, self).__init__(parent)
        self.command = command
        self.widget = QtWidgets.QTextBrowser()
        self.widget.setReadOnly(True)
        self.widget.setText(command)
        self.widget.setDisabled(not enabled)
        font_height = QtGui.QFontMetrics(self.widget.document().defaultFont()).height()
        lines = math.ceil(len(command) / 200)
        self.setMinimumHeight(int(font_height + ((lines + 2) * (font_height * 1.25))))

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(f"Command {number}" if not name else name), 0, 0, 1, 2)
        grid.addWidget(self.widget, 1, 0, 1, 2)
        self.setLayout(grid)


class CommandList(QtWidgets.QWidget):
    def __init__(self, parent):
        super(CommandList, self).__init__(parent)
        self.video_options = parent

        layout = QtWidgets.QGridLayout()

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Commands to execute"))

        copy_commands_button = QtWidgets.QPushButton(
            self.style().standardIcon(QtWidgets.QStyle.SP_ToolBarVerticalExtensionButton), "Copy Commands"
        )
        copy_commands_button.setToolTip("Copy all commands to the clipboard")
        copy_commands_button.clicked.connect(lambda: self.copy_commands_to_clipboard())

        save_commands_button = QtWidgets.QPushButton(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), "Save Commands"
        )
        save_commands_button.setToolTip("Save commands to file")
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
        return f"\r\n".join(self.commands) if reusables.win_based else f"\n".join(self.commands)

    def copy_commands_to_clipboard(self):
        cmds = self._prep_commands()
        self.video_options.main.container.app.clipboard().setText(cmds)

    @reusables.log_exception("fastflix", show_traceback=False)
    def save_commands_to_file(self):
        ext = ".bat" if reusables.win_based else ".sh"
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, caption="Save Video As", directory=str(Path("~").expanduser()), filter=f"Save File (*{ext})"
        )
        if filename and filename[0]:
            Path(filename[0]).write_text(self._prep_commands())

    def update_commands(self, commands):
        if not commands:
            return
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
                self.commands.append(item.command)
                layout.addWidget(new_item)
            elif item.item == "loop":
                new_item = Loop(self.scroll_area, item.condition, item.commands, index, name=item.name)
                layout.addWidget(new_item)
        layout.addStretch()
        self.inner_widget.setLayout(layout)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super(CommandList, self).resizeEvent(event)
