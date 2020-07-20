#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import pkg_resources

from fastflix.shared import QtWidgets, QtGui
from fastflix.widgets.main import Main
from fastflix.widgets.about import About
from fastflix.widgets.logs import Logs


class Container(QtWidgets.QMainWindow):
    def __init__(self, data_path, work_path, **kwargs):
        super(Container, self).__init__()
        self.logs = Logs()
        self.about = None
        self.init_menu()
        main = Main(self, data_path, work_path, **kwargs)
        self.setCentralWidget(main)
        self.setMinimumSize(1200, 600)
        my_data = str(Path(pkg_resources.resource_filename(__name__, f"../data/icon.ico")).resolve())
        icon = QtGui.QIcon(my_data)
        self.setWindowIcon(icon)
        self.setWindowIcon(icon)

    def init_menu(self):
        exit_action = QtWidgets.QAction("&Exit", self)
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(exit_action)

        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self.show_about)

        log_action = QtWidgets.QAction("View &Logs", self)
        log_action.triggered.connect(self.show_logs)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(log_action)
        help_menu.addAction(about_action)

    def show_about(self):
        self.about = About()
        self.about.show()

    def show_logs(self):
        self.logs.show()
