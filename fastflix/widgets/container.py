#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path
from subprocess import run
from dataclasses import asdict

import pkg_resources
import reusables
from box import Box
from appdirs import user_data_dir
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
from fastflix.exceptions import FastFlixInternalException

logger = logging.getLogger("fastflix")


class Container(QtWidgets.QMainWindow):
    def __init__(self, app: FastFlixApp, **kwargs):
        super().__init__(None)
        self.app = app

        self.logs = Logs()
        self.changes = Changes()
        self.about = None
        self.profile_details = None

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
        self.main.close(from_container=True)
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
        new_profile_action.triggered.connect(self.new_profile)

        show_profile_action = QtWidgets.QAction("Current Profile Settings", self)
        show_profile_action.triggered.connect(self.show_profile)

        delete_profile_action = QtWidgets.QAction("Delete Current Profile", self)
        delete_profile_action.triggered.connect(self.delete_profile)
        profile_menu.addAction(new_profile_action)
        profile_menu.addAction(show_profile_action)
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
        self.setting = Settings(self.app, self.main)
        self.setting.show()

    def new_profile(self):
        self.profile.show()

    def show_profile(self):
        self.profile_details = ProfileDetails(self.app.fastflix.config.profile)
        self.profile_details.show()

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
        ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True)) / "bin"
        ffmpeg = ffmpeg_folder / "ffmpeg.exe"
        ffprobe = ffmpeg_folder / "ffprobe.exe"
        try:
            ProgressBar(self.app, [Task(t("Downloading FFmpeg"), latest_ffmpeg)], signal_task=True, can_cancel=True)
        except FastFlixInternalException:
            print("Caught")
            pass
        except Exception as err:
            message(f"Could not download the newest FFmpeg: {err}")
        else:
            if not ffmpeg.exists() or not ffprobe.exists():
                message(f"Could not locate the downloaded files at {ffmpeg_folder}!")
            else:
                self.app.fastflix.config.ffmpeg = ffmpeg
                self.app.fastflix.config.ffprobe = ffprobe


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


class ProfileDetails(QtWidgets.QWidget):
    def profile_widget(self, settings):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        for k, v in asdict(settings).items():
            item_1 = QtWidgets.QLabel(str(k))
            item_2 = QtWidgets.QLabel(str(v))
            inner_layout = QtWidgets.QHBoxLayout()
            inner_layout.addWidget(item_1)
            inner_layout.addWidget(item_2)
            layout.addLayout(inner_layout)
        widget.setLayout(layout)
        return widget

    def __init__(self, profile):
        super().__init__(None)
        self.layout = QtWidgets.QHBoxLayout(self)

        main_section = QtWidgets.QVBoxLayout(self)
        for k, v in asdict(profile).items():
            if k not in profile.setting_types.keys():
                item_1 = QtWidgets.QLabel(str(k))
                item_2 = QtWidgets.QLabel(str(v))
                inner_layout = QtWidgets.QHBoxLayout()
                inner_layout.addWidget(item_1)
                inner_layout.addWidget(item_2)
                main_section.addLayout(inner_layout)
        self.layout.addLayout(main_section)

        for setting_name in profile.setting_types.keys():
            setting = getattr(profile, setting_name)
            if setting:
                self.layout.addWidget(self.profile_widget(setting))
        # self.tab2 = QtWidgets.QWidget()
        # self.tabs.resize(300, 200)

        # Add tabs

        # self.tabs.addTab(self.tab2, "Tab 2")

        # # Create first tab
        # self.tab1.layout = QVBoxLayout(self)
        # self.pushButton1 = QPushButton("PyQt5 button")
        # self.tab1.layout.addWidget(self.pushButton1)
        # self.tab1.setLayout(self.tab1.layout)

        self.setLayout(self.layout)
