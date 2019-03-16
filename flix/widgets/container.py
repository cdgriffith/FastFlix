#!/usr/bin/env python
import logging
import os

from flix.shared import QtWidgets, QtGui, pyinstaller, base_path, message
from flix.widgets.main import Main
from flix.widgets.about import About


class Container(QtWidgets.QMainWindow):

    def __init__(self, parent=None, **kwargs):
        super(Container, self).__init__(parent)
        self.init_menu()
        main = Main(self)
        self.setCentralWidget(main)
        #self.setFixedSize(1440, 800)
        self.setMinimumSize(1000, 600)
        self.about = QtWidgets.QWidget()

    def init_menu(self):
        exit_action = QtWidgets.QAction('&Exit', self)
        exit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

        about_action = QtWidgets.QAction('&About', self)
        about_action.triggered.connect(self.show_about)

        help_menu = menubar.addMenu('&Help')
        help_menu.addAction(about_action)

    def show_about(self):
        self.about = About()
        self.about.show()
