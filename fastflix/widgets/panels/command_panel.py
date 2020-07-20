#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box

from fastflix.shared import QtGui, QtCore, QtWidgets, error_message, main_width


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
        self.widget = QtWidgets.QLineEdit()
        self.widget.setReadOnly(True)
        self.widget.setText(command)
        self.widget.setDisabled(not enabled)
        self.setFixedHeight(60)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(f"Command {number}" if not name else name), 0, 0, 1, 2)
        grid.addWidget(self.widget, 1, 0, 1, 2)
        self.setLayout(grid)


class CommandList(QtWidgets.QWidget):
    def __init__(self, parent):
        super(CommandList, self).__init__(parent)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Commands to execute"))

        self.inner_widget = QtWidgets.QWidget()

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setMinimumHeight(200)

        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def update_commands(self, commands):
        if not commands:
            return
        self.inner_widget = QtWidgets.QWidget()
        sp = QtWidgets.QSizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        self.inner_widget.setSizePolicy(sp)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)
        for index, item in enumerate(commands, 1):
            if item.item == "command":
                new_item = Command(self.scroll_area, item.command, index, name=item.name)
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
