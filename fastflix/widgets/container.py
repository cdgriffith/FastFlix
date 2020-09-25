#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path
from subprocess import run

import pkg_resources
import reusables
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.shared import latest_fastflix, message
from fastflix.widgets.about import About
from fastflix.widgets.changes import Changes
from fastflix.widgets.logs import Logs
from fastflix.widgets.main import Main
from fastflix.widgets.settings import Settings

logger = logging.getLogger("fastflix")


class Container(QtWidgets.QMainWindow):
    def __init__(self, data_path, work_path, config_file, main_app, **kwargs):
        super().__init__()
        self.app = main_app
        self.log_dir = data_path / "logs"
        self.logs = Logs()
        self.changes = Changes()
        self.about = None
        self.init_menu()
        self.config_file = config_file
        self.main = Main(self, data_path, work_path, **kwargs)
        self.setCentralWidget(self.main)
        self.setMinimumSize(1200, 600)
        my_data = str(Path(pkg_resources.resource_filename(__name__, f"../data/icon.ico")).resolve())
        self.icon = QtGui.QIcon(my_data)
        self.setWindowIcon(self.icon)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.main.converting:
            sm = QtWidgets.QMessageBox()
            sm.setText("<h2>There is a conversion in process!</h2>")
            sm.addButton("Cancel Conversion", QtWidgets.QMessageBox.RejectRole)
            sm.addButton("Close GUI Only", QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton("Keep FastFlix Open", QtWidgets.QMessageBox.AcceptRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel Conversion":
                self.main.worker_queue.put(["cancel"])
                self.main.close()
            elif sm.clickedButton().text() == "Close GUI Only":
                self.main.close(no_cleanup=True)
                return super(Container, self).closeEvent(a0)
            else:
                a0.ignore()
                return

        for item in self.main.path.work.iterdir():
            if item.is_dir() and item.stem.startswith("temp_"):
                shutil.rmtree(item, ignore_errors=True)
            if item.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                item.unlink()
        super(Container, self).closeEvent(a0)

    def init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        setting_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogListView), "&Settings", self
        )
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

        about_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogInfoView), "&About", self
        )
        about_action.triggered.connect(self.show_about)

        changes_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), "View &Changes", self
        )
        changes_action.triggered.connect(self.show_changes)

        log_dir_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton), "Open Log Directory", self
        )
        log_dir_action.triggered.connect(self.show_log_dir)

        log_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), "View GUI Debug &Logs", self
        )
        log_action.triggered.connect(self.show_logs)

        report_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogHelpButton), "Report &Issue", self
        )
        report_action.triggered.connect(self.open_issues)

        version_action = QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload), "Check for Newer Version of FastFlix", self
        )
        version_action.triggered.connect(lambda: latest_fastflix(no_new_dialog=True))

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(changes_action)
        help_menu.addAction(report_action)
        help_menu.addAction(log_dir_action)
        help_menu.addAction(log_action)
        help_menu.addSeparator()
        help_menu.addAction(version_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

    def show_about(self):
        self.about = About()
        self.about.show()

    def show_setting(self):
        self.setting = Settings(self.config_file, self.main)
        self.setting.show()

    def show_logs(self):
        self.logs.show()

    def show_changes(self):
        self.changes.show()

    def open_issues(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/issues"))

    def show_log_dir(self):
        OpenFolder(self, self.log_dir).run()


class OpenFolder(QtCore.QThread):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.app = parent
        self.path = str(path)

    def __del__(self):
        self.wait()

    def run(self):
        if reusables.win_based:
            run(["explorer", self.path])
            # Also possible through ctypes shell extension
            # import ctypes
            #
            # ctypes.windll.ole32.CoInitialize(None)
            # pidl = ctypes.windll.shell32.ILCreateFromPathW(self.path)
            # ctypes.windll.shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
            # ctypes.windll.shell32.ILFree(pidl)
            # ctypes.windll.ole32.CoUninitialize()
        elif sys.platform == "darwin":
            run(["open", self.path])
        else:
            run(["xdg-open", self.path])
