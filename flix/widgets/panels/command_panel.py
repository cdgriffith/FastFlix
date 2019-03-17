#!/usr/bin/env python

from box import Box

from flix.shared import QtGui, QtCore, QtWidgets, error_message, main_width


class Loop(QtWidgets.QWidget):

    def __init__(self, parent, type, condition, commands):
        super(Loop, self).__init__(parent)
        # TODO loops


class Command(QtWidgets.QTabWidget):

    def __init__(self, parent, command, number, enabled=True):
        super(Command, self).__init__(parent)
        self.command = command
        self.widget = QtWidgets.QLineEdit()
        self.widget.setText(command)
        self.widget.setDisabled(not enabled)
        self.setFixedHeight(60)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(f"Command {number}"), 0, 0, 1, 2)
        grid.addWidget(self.widget, 1, 0, 1, 2)
        self.setLayout(grid)


class CommandList(QtWidgets.QWidget):

    def __init__(self, parent):
        super(CommandList, self).__init__(parent)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel('Commands to execute'))

        self.inner_widget = QtWidgets.QWidget()

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setMinimumHeight(200)

        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def update_commands(self, commands):
        self.inner_widget = QtWidgets.QWidget()
        sp = QtWidgets.QSizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Maximum)
        self.inner_widget.setSizePolicy(sp)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(5)
        # TODO handle new loop thing
        for index, command in enumerate(commands, 1):
            new_item = Command(self.scroll_area, command.command, index)
            layout.addWidget(new_item)
        layout.addStretch()
        self.inner_widget.setLayout(layout)
        self.scroll_area.setWidget(self.inner_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self.inner_widget.setFixedWidth(self.scroll_area.width() - 3)
        return super(CommandList, self).resizeEvent(event)