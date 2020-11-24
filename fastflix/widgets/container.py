#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path
from subprocess import run

import pkg_resources
import reusables
from box import Box
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import latest_ffmpeg
from fastflix.resources import main_icon
from fastflix.shared import latest_fastflix, message
from fastflix.widgets.about import About
from fastflix.widgets.changes import Changes
from fastflix.widgets.logs import Logs
from fastflix.widgets.main import Main
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.widgets.settings import Settings
from fastflix.widgets.profile_window import ProfileWindow

logger = logging.getLogger("fastflix")


class Container(QtWidgets.QMainWindow):
    def __init__(self, app: FastFlixApp, **kwargs):
        super().__init__(None)
        self.app = app

        self.logs = Logs()
        self.changes = Changes()
        self.about = None

        self.init_menu()

        self.main = Main(self, app)
        self.profile = ProfileWindow(self.app, self.main)

        self.setCentralWidget(self.main)
        # self.setMinimumSize(QtCore.QSize(1000, 650))
        self.setFixedSize(QtCore.QSize(1150, 620))
        self.icon = QtGui.QIcon(main_icon)
        self.setWindowIcon(self.icon)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.main.converting:
            sm = QtWidgets.QMessageBox()
            sm.setText(f"<h2>{t('There is a conversion in process!')}</h2>")
            sm.addButton(t("Cancel Conversion"), QtWidgets.QMessageBox.RejectRole)
            sm.addButton(t("Close GUI Only"), QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton(t("Keep FastFlix Open"), QtWidgets.QMessageBox.AcceptRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel Conversion":
                self.app.fastflix.worker_queue.put(["cancel"])
                self.main.close()
            elif sm.clickedButton().text() == "Close GUI Only":
                self.main.close(no_cleanup=True)
                return super(Container, self).closeEvent(a0)
            else:
                a0.ignore()
                return

        for item in self.app.fastflix.config.work_path.iterdir():
            if item.is_dir() and item.stem.startswith("temp_"):
                shutil.rmtree(item, ignore_errors=True)
            if item.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                item.unlink()
        super(Container, self).closeEvent(a0)

    def si(self, widget):
        return self.style().standardIcon(widget)

    def init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        setting_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogListView), "&Settings", self)
        setting_action.setShortcut("Ctrl+S")
        setting_action.triggered.connect(self.show_setting)

        exit_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogCancelButton), "&Exit", self)
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)

        file_menu.addAction(setting_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        profile_menu = menubar.addMenu("&Profiles")
        new_profile_action = QtWidgets.QAction("New Profile", self)
        new_profile_action.triggered.connect(self.show_profile)

        delete_profile_action = QtWidgets.QAction("Delete Current Profile", self)
        delete_profile_action.triggered.connect(self.delete_profile)
        profile_menu.addAction(new_profile_action)
        profile_menu.addAction(delete_profile_action)

        about_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogInfoView), "&About", self)
        about_action.triggered.connect(self.show_about)

        changes_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), "View &Changes", self)
        changes_action.triggered.connect(self.show_changes)

        log_dir_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogOpenButton), "Open Log Directory", self)
        log_dir_action.triggered.connect(self.show_log_dir)

        log_action = QtWidgets.QAction(
            self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), "View GUI Debug &Logs", self
        )
        log_action.triggered.connect(self.show_logs)

        report_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogHelpButton), "Report &Issue", self)
        report_action.triggered.connect(self.open_issues)

        version_action = QtWidgets.QAction(
            self.si(QtWidgets.QStyle.SP_BrowserReload), "Check for Newer Version of FastFlix", self
        )
        version_action.triggered.connect(lambda: latest_fastflix(no_new_dialog=True))

        ffmpeg_update_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_ArrowDown), "Download Newest FFmpeg", self)
        ffmpeg_update_action.triggered.connect(self.download_ffmpeg)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(changes_action)
        help_menu.addAction(report_action)
        help_menu.addAction(log_dir_action)
        help_menu.addAction(log_action)
        help_menu.addSeparator()
        help_menu.addAction(version_action)
        if reusables.win_based:
            help_menu.addAction(ffmpeg_update_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

    def show_about(self):
        self.about = About()
        self.about.show()

    def show_setting(self):
        self.setting = Settings(self.app)
        self.setting.show()

    def show_profile(self):
        self.profile.show()

    def delete_profile(self):
        self.profile.delete_current_profile()

    def show_logs(self):
        self.logs.show()

    def show_changes(self):
        self.changes.show()

    def open_issues(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/issues"))

    def show_log_dir(self):
        OpenFolder(self, str(self.app.fastflix.log_path)).run()

    def download_ffmpeg(self):
        ProgressBar(self.app, [Task(t("Downloading FFmpeg"), latest_ffmpeg)], signal_task=True)


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
