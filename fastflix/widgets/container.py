#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import pkg_resources

from qtpy import QtCore, QtWidgets, QtGui
from fastflix.widgets.main import Main
from fastflix.widgets.about import About
from fastflix.widgets.logs import Logs
from fastflix.widgets.settings import Settings


class Container(QtWidgets.QMainWindow):
    def __init__(self, data_path, work_path, config_file, **kwargs):
        super(Container, self).__init__()
        self.logs = Logs()
        self.about = None
        self.init_menu()
        self.config_file = config_file
        self.main = Main(self, data_path, work_path, **kwargs)
        self.setCentralWidget(self.main)
        self.setMinimumSize(1200, 600)
        my_data = str(Path(pkg_resources.resource_filename(__name__, f"../data/icon.ico")).resolve())
        icon = QtGui.QIcon(my_data)
        self.setWindowIcon(icon)
        self.setWindowIcon(icon)

    def init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        setting_action = QtWidgets.QAction("&Settings", self)
        setting_action.setShortcut("Ctrl+S")
        setting_action.triggered.connect(self.show_setting)

        exit_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton), "&Exit", self
        )
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)

        file_menu.addAction(setting_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self.show_about)

        log_action = QtWidgets.QAction("View &Logs", self)
        log_action.triggered.connect(self.show_logs)

        report_action = QtWidgets.QAction("Report &Issue", self)
        report_action.triggered.connect(self.open_issues)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(log_action)
        help_menu.addAction(report_action)
        help_menu.addAction(about_action)

    def show_about(self):
        self.about = About()
        self.about.show()

    def show_setting(self):
        self.setting = Settings(self.config_file, self.main)
        self.setting.show()

    def show_logs(self):
        self.logs.show()

    def open_issues(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/issues"))
