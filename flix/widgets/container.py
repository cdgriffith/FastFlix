#!/usr/bin/env python
import logging
import os

from flix.shared import QtWidgets, QtGui, pyinstaller, base_path, message
from flix.widgets.main2 import Main


class Container(QtWidgets.QMainWindow):

    def __init__(self, parent=None, **kwargs):
        super(Container, self).__init__(parent)
        self.init_menu()
        main = Main(self)
        self.setCentralWidget(main)
        #self.setFixedSize(1440, 800)
        self.setMinimumSize(1200, 800)

    def init_menu(self):
        exit_action = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu('&Settings')
