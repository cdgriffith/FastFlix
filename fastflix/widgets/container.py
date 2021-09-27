#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from subprocess import run

import reusables
from appdirs import user_data_dir
from qtpy import QtCore, QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.config import setting_types
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import latest_ffmpeg
from fastflix.resources import main_icon
from fastflix.shared import clean_logs, error_message, latest_fastflix, message
from fastflix.windows_tools import cleanup_windows_notification
from fastflix.widgets.about import About
from fastflix.widgets.changes import Changes
from fastflix.widgets.logs import Logs
from fastflix.widgets.main import Main
from fastflix.widgets.profile_window import ProfileWindow
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.widgets.settings import Settings

logger = logging.getLogger("fastflix")


class Container(QtWidgets.QMainWindow):
    def __init__(self, app: FastFlixApp, **kwargs):
        super().__init__(None)
        self.app = app
        self.pb = None

        self.logs = Logs()
        self.changes = Changes()
        self.about = None
        self.profile_details = None

        self.init_menu()

        self.main = Main(self, app)
        self.profile = ProfileWindow(self.app, self.main)

        self.setCentralWidget(self.main)
        self.setMinimumSize(QtCore.QSize(1280, 700))
        self.icon = QtGui.QIcon(main_icon)
        self.setWindowIcon(self.icon)
        self.main.set_profile()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.pb:
            try:
                self.pb.stop_signal.emit()
            except Exception:
                pass
        if self.main.converting:
            sm = QtWidgets.QMessageBox()
            sm.setText(f"<h2>{t('There is a conversion in process!')}</h2>")
            sm.addButton(t("Cancel Conversion"), QtWidgets.QMessageBox.RejectRole)
            sm.addButton(t("Close GUI Only"), QtWidgets.QMessageBox.DestructiveRole)
            sm.addButton(t("Keep FastFlix Open"), QtWidgets.QMessageBox.AcceptRole)
            sm.exec_()
            if sm.clickedButton().text() == "Cancel Conversion":
                self.app.fastflix.worker_queue.put(["cancel"])
                time.sleep(0.5)
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
            if item.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif")):
                item.unlink()
        if reusables.win_based:
            cleanup_windows_notification()
        self.main.close(from_container=True)
        super(Container, self).closeEvent(a0)

    def si(self, widget):
        return self.style().standardIcon(widget)

    def init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu(t("File"))

        setting_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogListView), t("Settings"), self)
        setting_action.setShortcut("Ctrl+S")
        setting_action.triggered.connect(self.show_setting)

        exit_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogCancelButton), t("Exit"), self)
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip(t("Exit application"))
        exit_action.triggered.connect(self.close)

        file_menu.addAction(setting_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        profile_menu = menubar.addMenu(t("Profiles"))
        new_profile_action = QtWidgets.QAction(t("New Profile"), self)
        new_profile_action.triggered.connect(self.new_profile)

        show_profile_action = QtWidgets.QAction(t("Current Profile Settings"), self)
        show_profile_action.triggered.connect(self.show_profile)

        delete_profile_action = QtWidgets.QAction(t("Delete Current Profile"), self)
        delete_profile_action.triggered.connect(self.delete_profile)
        profile_menu.addAction(new_profile_action)
        profile_menu.addAction(show_profile_action)
        profile_menu.addAction(delete_profile_action)

        wiki_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogInfoView), t("FastFlix Wiki"), self)
        wiki_action.triggered.connect(self.show_wiki)

        about_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogInfoView), t("About"), self)
        about_action.triggered.connect(self.show_about)

        changes_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), t("View Changes"), self)
        changes_action.triggered.connect(self.show_changes)

        log_dir_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogOpenButton), t("Open Log Directory"), self)
        log_dir_action.triggered.connect(self.show_log_dir)

        log_action = QtWidgets.QAction(
            self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), t("View GUI Debug Logs"), self
        )
        log_action.triggered.connect(self.show_logs)

        report_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogHelpButton), t("Report Issue"), self)
        report_action.triggered.connect(self.open_issues)

        version_action = QtWidgets.QAction(
            self.si(QtWidgets.QStyle.SP_BrowserReload), t("Check for Newer Version of FastFlix"), self
        )
        version_action.triggered.connect(lambda: latest_fastflix(no_new_dialog=True))

        ffmpeg_update_action = QtWidgets.QAction(
            self.si(QtWidgets.QStyle.SP_ArrowDown), t("Download Newest FFmpeg"), self
        )
        ffmpeg_update_action.triggered.connect(self.download_ffmpeg)

        clean_logs_action = QtWidgets.QAction(self.si(QtWidgets.QStyle.SP_DialogResetButton), t("Clean Old Logs"), self)
        clean_logs_action.triggered.connect(self.clean_old_logs)

        help_menu = menubar.addMenu(t("Help"))
        help_menu.addAction(wiki_action)
        help_menu.addSeparator()
        help_menu.addAction(changes_action)
        help_menu.addAction(report_action)
        help_menu.addAction(log_dir_action)
        help_menu.addAction(log_action)
        help_menu.addAction(clean_logs_action)
        help_menu.addSeparator()
        help_menu.addAction(version_action)
        if reusables.win_based:
            help_menu.addAction(ffmpeg_update_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

    def show_wiki(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/wiki"))

    def show_about(self):
        self.about = About(app=self.app)
        self.about.show()

    def show_setting(self):
        self.setting = Settings(self.app, self.main)
        self.setting.show()

    def new_profile(self):
        self.profile.show()

    def show_profile(self):
        self.profile_details = ProfileDetails(
            self.app.fastflix.config.selected_profile, self.app.fastflix.config.profile
        )
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
            self.pb = ProgressBar(
                self.app, [Task(t("Downloading FFmpeg"), latest_ffmpeg)], signal_task=True, can_cancel=True
            )
        except FastFlixInternalException:
            pass
        except Exception as err:
            message(f"{t('Could not download the newest FFmpeg')}: {err}")
        else:
            if not ffmpeg.exists() or not ffprobe.exists():
                message(f"{t('Could not locate the downloaded files at')} {ffmpeg_folder}!")
            else:
                self.app.fastflix.config.ffmpeg = ffmpeg
                self.app.fastflix.config.ffprobe = ffprobe
        self.pb = None

    def clean_old_logs(self):
        try:
            self.pb = ProgressBar(self.app, [Task(t("Clean Old Logs"), clean_logs)], signal_task=True, can_cancel=False)
        except Exception:
            error_message(t("Could not compress old logs"), traceback=True)
        self.pb = None


class OpenFolder(QtCore.QThread):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.app = parent
        self.path = str(path)

    def __del__(self):
        try:
            self.wait()
        except BaseException:
            pass

    def run(self):
        try:
            if reusables.win_based:
                run(["explorer", self.path])
            elif sys.platform == "darwin":
                run(["open", self.path])
            else:
                run(["xdg-open", self.path])
        except FileNotFoundError:
            logger.error(f"Do not know which command to use to open: {self.path}")


class ProfileDetails(QtWidgets.QWidget):
    def profile_widget(self, settings):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(t("Encoder Settings"))
        title.setFont(QtGui.QFont("helvetica", 9, weight=70))
        layout.addWidget(title)
        for k, v in settings.dict().items():
            item_1 = QtWidgets.QLabel(" ".join(str(k).split("_")).title())
            item_2 = QtWidgets.QLabel(str(v))
            item_2.setMaximumWidth(150)
            inner_layout = QtWidgets.QHBoxLayout()
            inner_layout.addWidget(item_1)
            inner_layout.addWidget(item_2)
            layout.addLayout(inner_layout)
        widget.setLayout(layout)
        return widget

    def __init__(self, profile_name, profile):
        super().__init__(None)
        self.layout = QtWidgets.QHBoxLayout(self)

        main_section = QtWidgets.QVBoxLayout(self)
        profile_title = QtWidgets.QLabel(f"{t('Profile_window')}: {profile_name}")
        profile_title.setFont(QtGui.QFont("helvetica", 10, weight=70))
        main_section.addWidget(profile_title)
        for k, v in profile.dict().items():
            if k not in setting_types.keys():
                item_1 = QtWidgets.QLabel(" ".join(str(k).split("_")).title())
                item_2 = QtWidgets.QLabel(str(v))
                item_2.setMaximumWidth(150)
                inner_layout = QtWidgets.QHBoxLayout()
                inner_layout.addWidget(item_1)
                inner_layout.addWidget(item_2)
                main_section.addLayout(inner_layout)
        self.layout.addLayout(main_section)

        splitter = QtWidgets.QWidget()
        splitter.setMaximumWidth(1)
        splitter.setStyleSheet("background-color: #999999")
        self.layout.addWidget(splitter)

        for setting_name in setting_types.keys():
            setting = getattr(profile, setting_name)
            if setting:
                self.layout.addWidget(self.profile_widget(setting))
        self.setMinimumWidth(780)
        self.setLayout(self.layout)
