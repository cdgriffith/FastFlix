#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import sys
from pathlib import Path

import reusables
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.encoders.common.helpers import Command as BuilderCommand

done_actions = {
    "linux": {
        "shutdown": 'shutdown -h 1 "FastFlix conversion complete, shutting down"',
        "restart": 'shutdown -r 1 "FastFlix conversion complete, rebooting"',
        "logout": "logout",
        "sleep": "pm-suspend",
        "hibernate": "pm-hibernate",
    },
    "windows": {
        "shutdown": "shutdown /s",
        "restart": "shutdown /r",
        "logout": "shutdown /l",
        "hibernate": "shutdown /h",
    },
}


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
    def __init__(self, parent, command, number, name="", enabled=True, after_done=False, height=None):
        super(Command, self).__init__(parent)
        self.command = command
        self.after_done = after_done
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
        self.label = QtWidgets.QLabel(f"Command {self.number}" if not self.name else self.name)
        self.update_grid()
        self.widget.setDisabled(not enabled)

    def update_grid(self):
        grid = QtWidgets.QVBoxLayout()
        self.label.setText(f"Command {self.number}" if not self.name else self.name)
        grid.addWidget(self.label)
        grid.addWidget(self.widget)
        grid.addStretch()
        self.setLayout(grid)
        self.widget.setText(self.command)


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

        self.after_done_combo = QtWidgets.QComboBox()
        self.after_done_combo.addItem("None")
        actions = set()
        if reusables.win_based:
            actions.update(done_actions["windows"].keys())

        elif sys.platform == "darwin":
            actions.update(["shutdown", "restart"])
        else:
            actions.update(done_actions["linux"].keys())
        if "custom_after_run_scripts" in self.video_options.main.config:
            actions.update(self.video_options.main.config.custom_after_run_scripts)

        self.after_done_combo.addItems(sorted(actions))
        self.after_done_combo.setToolTip("Run a command after conversion completes")
        self.after_done_combo.currentIndexChanged.connect(lambda: self.set_after_done())
        self.after_done_combo.setDisabled(True)
        self.after_done_widget = None

        top_row.addStretch()

        top_row.addWidget(copy_commands_button)
        top_row.addWidget(save_commands_button)
        top_row.addWidget(QtWidgets.QLabel("After Conversion: "))
        top_row.addWidget(self.after_done_combo)

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
            self, caption="Save Video As", directory=str(Path("~").expanduser()), filter=f"Save File (*{ext})"
        )
        if filename and filename[0]:
            Path(filename[0]).write_text(self._prep_commands())

    def after_done(self, builder=False):
        if self.after_done_widget is None:
            return
        option = self.after_done_combo.currentText()
        custom = (
            self.video_options.main.config.custom_after_run_scripts
            if "custom_after_run_scripts" in self.video_options.main.config
            else {}
        )
        if option == "None":
            return
        if option in custom:
            command = custom[option]
        elif reusables.win_based:
            command = done_actions["windows"][option]
        else:
            command = done_actions["linux"][option]

        if builder:
            return BuilderCommand(command, [], False, shell=True)
        return command

    @reusables.log_exception("fastflix", show_traceback=False)
    def set_after_done(self):
        if self.after_done_widget is None:
            return
        option = self.after_done_combo.currentText()

        if option == "None":
            self.after_done_widget.hide()
            self.after_done_widget.name = "hidden"
            return
        self.after_done_widget.number = len(self.commands)
        self.after_done_widget.name = option
        self.after_done_widget.command = self.after_done()
        self.after_done_widget.show()
        self.after_done_widget.update_grid()

    def update_commands(self, commands):
        if not commands:
            return
        self.after_done_combo.setEnabled(True)
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
        if self.after_done_widget is None:
            self.after_done_widget = Command(
                self.scroll_area, "echo 'done'", len(self.commands) + 1, name="hidden", height=70
            )
        self.commands.append(self.after_done_widget)
        self.after_done_widget.show()  # Have to show then re-hide to get sizing event properly
        layout.addWidget(self.after_done_widget)
        layout.addStretch()
        self.inner_widget.setLayout(layout)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        self.after_done_widget.hide()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super(CommandList, self).resizeEvent(event)
