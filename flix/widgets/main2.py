#!/usr/bin/env python
import logging
import os

from flix.shared import QtWidgets, QtGui, pyinstaller, base_path, message


class Main(QtWidgets.QMainWindow):

    def __init__(self, parent=None, **kwargs):
        super(Main, self).__init__(parent)

        self.input_file = None
        self.start_time = 0
        self.duration = None

        self.input_file_widget = None

        self.grid = QtWidgets.QGridLayout()


        self.init_menu()
        self.init_input_file()

        self.grid.addWidget(QtWidgets.QLineEdit("test"))

        self.setLayout(self.grid)
        self.setCentralWidget(QtWidgets.QLineEdit("test"))
        #self.setFixedSize(1400, 800)
        self.show()


    def init_menu(self):
        exit_action = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu('&Settings')

    def init_input_file(self):
        #input_file_layout = QtWidgets.QHBoxLayout()
        self.input_file_widget = QtWidgets.QLineEdit("")
        self.input_file_widget.setReadOnly(True)
        self.input_file_widget.setFixedWidth(400)
        open_input_file = QtWidgets.QPushButton("...")
        # if not source:
        open_input_file.setDefault(True)
        #input_file_layout.addWidget(QtWidgets.QLabel("Source File:"))
        #input_file_layout.addWidget(self.input_file_widget)
        #input_file_layout.addWidget(open_input_file)
        #input_file_layout.setSpacing(20)
        open_input_file.clicked.connect(lambda: self.open_file(self.input_file_widget))
        # self.grid.addLayout(input_file_layout, 1, 1, 1, 1)
        #self.input_file_widget.show()
        self.grid.addWidget(self.input_file_widget, 1, 1)
        #self.grid.addWidget(open_input_file, 1, 2)

    def open_file(self, file):
        pass
