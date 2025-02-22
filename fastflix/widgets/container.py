#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
import sys
import time
from pathlib import Path
from subprocess import run

import reusables
from appdirs import user_data_dir
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QAction

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.config import setting_types, get_preset_defaults
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.program_downloads import latest_ffmpeg, grab_stable_ffmpeg
from fastflix.resources import main_icon, get_icon, changes_file, local_changes_file, local_package_changes_file
from fastflix.shared import clean_logs, error_message, latest_fastflix, message, yes_no_message
from fastflix.widgets.about import About
from fastflix.widgets.changes import Changes

# from fastflix.widgets.logs import Logs
from fastflix.widgets.main import Main
from fastflix.widgets.windows.profile_window import ProfileWindow
from fastflix.widgets.progress_bar import ProgressBar, Task
from fastflix.widgets.settings import Settings
from fastflix.widgets.windows.concat import ConcatWindow
from fastflix.widgets.windows.multiple_files import MultipleFilesWindow

# from fastflix.widgets.windows.hdr10plus_inject import HDR10PlusInjectWindow

logger = logging.getLogger("fastflix")


class Container(QtWidgets.QMainWindow):
    def __init__(self, app: FastFlixApp, **kwargs):
        super().__init__(None)
        self.app = app
        self.pb = None
        self.profile_window = None

        self.app.setApplicationName("FastFlix")
        self.app.setWindowIcon(QtGui.QIcon(main_icon))

        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon(main_icon))

        show_action = QAction(t("Open FastFlix"), self)
        quit_action = QAction(t("Exit"), self)
        hide_action = QAction(t("Minimize to Tray"), self)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(self.close)
        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.tray_icon.setToolTip("FastFlix")

        if self.app.fastflix.config.stay_on_top:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        # self.logs = Logs()
        self.changes = None
        self.about = None
        self.profile_details = None

        self.init_menu()

        self.main = Main(self, app)

        self.setCentralWidget(self.main)
        self.setBaseSize(QtCore.QSize(1350, 750))
        self.icon = QtGui.QIcon(main_icon)
        self.setWindowIcon(self.icon)
        self.main.set_profile()

        if self.app.fastflix.config.theme == "onyx":
            self.setStyleSheet(
                """
                QAbstractItemView{ background-color: #4b5054; }
                QPushButton{ border-radius:10px; }
                QLineEdit{ background-color: #707070; color: black; border-radius: 10px; }
                QTextEdit{ background-color: #707070; color: black; }
                QTabBar::tab{ background-color: #4b5054; }
                QComboBox{ border-radius:10px; }
                QScrollArea{ border: 1px solid #919191; }
                QWidget{font-size: 14px;}
                """
            )
        else:
            self.setStyleSheet(
                """
            QWidget{font-size: 14px;}
            """
            )
        # self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.moveFlag = False

    # def mousePressEvent(self, event):
    #     if event.button() == QtCore.Qt.LeftButton:
    #         self.moveFlag = True
    #         self.movePosition = event.globalPos() - self.pos()
    #         self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
    #         event.accept()
    #
    # def mouseMoveEvent(self, event):
    #     if QtCore.Qt.LeftButton and self.moveFlag:
    #         self.move(event.globalPos() - self.movePosition)
    #         event.accept()
    #
    # def mouseReleaseEvent(self, event):
    #     self.moveFlag = False
    #     self.setCursor(QtCore.Qt.ArrowCursor)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.app.fastflix.shutting_down = True
        if self.pb:
            try:
                self.pb.stop_signal.emit()
            except Exception:
                pass
        if self.app.fastflix.currently_encoding:
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
            if item.is_file() and item.name.startswith("concat_"):
                item.unlink(missing_ok=True)
            if item.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif")):
                item.unlink()
        shutil.rmtree(self.app.fastflix.config.work_path / "covers", ignore_errors=True)

        if self.app.fastflix.config.clean_old_logs:
            self.clean_old_logs(show_errors=False)
        self.main.close(from_container=True)
        super(Container, self).closeEvent(a0)

    def si(self, widget):
        return self.style().standardIcon(widget)

    def init_menu(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        menubar.setFixedWidth(360)
        menubar.setStyleSheet("font-size: 14px")

        file_menu = menubar.addMenu(t("File"))

        load_folder = QAction(self.si(QtWidgets.QStyle.SP_DirOpenIcon), t("Load Directory"), self)
        load_folder.triggered.connect(self.open_many)

        setting_action = QAction(self.si(QtWidgets.QStyle.SP_FileDialogListView), t("Settings"), self)
        setting_action.setShortcut("Ctrl+S")
        setting_action.triggered.connect(self.show_setting)

        self.stay_on_top_action = QAction(t("Stay on Top"), self)
        self.stay_on_top_action.triggered.connect(self.set_stay_top)
        if self.app.fastflix.config.stay_on_top:
            self.stay_on_top_action.setIcon(self.si(QtWidgets.QStyle.SP_DialogYesButton))
        else:
            self.stay_on_top_action.setIcon(self.si(QtWidgets.QStyle.SP_DialogNoButton))

        exit_action = QAction(self.si(QtWidgets.QStyle.SP_DialogCancelButton), t("Exit"), self)
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip(t("Exit application"))
        exit_action.triggered.connect(self.close)

        file_menu.addAction(load_folder)
        file_menu.addSeparator()
        file_menu.addAction(setting_action)
        file_menu.addSeparator()
        file_menu.addAction(self.stay_on_top_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        profile_menu = menubar.addMenu(t("Profiles"))
        new_profile_action = QAction(t("New Profile"), self)
        new_profile_action.triggered.connect(self.new_profile)

        show_profile_action = QAction(t("Current Profile Settings"), self)
        show_profile_action.triggered.connect(self.show_profile)

        delete_profile_action = QAction(t("Delete Current Profile"), self)
        delete_profile_action.triggered.connect(self.delete_profile)
        profile_menu.addAction(new_profile_action)
        profile_menu.addAction(show_profile_action)
        profile_menu.addAction(delete_profile_action)

        tools_menu = menubar.addMenu(t("Tools"))
        concat_action = QAction(
            QtGui.QIcon(get_icon("onyx-queue", self.app.fastflix.config.theme)), t("Concatenation Builder"), self
        )
        concat_action.triggered.connect(self.show_concat)
        tools_menu.addAction(concat_action)

        # hdr10p_inject_action = QAction(
        #     QtGui.QIcon(get_icon("onyx-queue", self.app.fastflix.config.theme)), t("HDR10+ Inject"), self
        # )
        # hdr10p_inject_action.triggered.connect(self.show_hdr10p_inject)
        # tools_menu.addAction(hdr10p_inject_action)

        wiki_action = QAction(self.si(QtWidgets.QStyle.SP_FileDialogInfoView), t("FastFlix Wiki"), self)
        wiki_action.triggered.connect(self.show_wiki)

        about_action = QAction(self.si(QtWidgets.QStyle.SP_FileDialogInfoView), t("About"), self)
        about_action.triggered.connect(self.show_about)

        changes_action = QAction(self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), t("View Changes"), self)
        changes_action.triggered.connect(self.show_changes)

        log_dir_action = QAction(self.si(QtWidgets.QStyle.SP_DialogOpenButton), t("Open Log Directory"), self)
        log_dir_action.triggered.connect(self.show_log_dir)

        # log_action = QAction(self.si(QtWidgets.QStyle.SP_FileDialogDetailedView), t("View GUI Debug Logs"), self)
        # log_action.triggered.connect(self.show_logs)

        report_action = QAction(self.si(QtWidgets.QStyle.SP_DialogHelpButton), t("Report Issue"), self)
        report_action.triggered.connect(self.open_issues)

        version_action = QAction(
            self.si(QtWidgets.QStyle.SP_BrowserReload), t("Check for Newer Version of FastFlix"), self
        )
        version_action.triggered.connect(lambda: latest_fastflix(show_new_dialog=True, app=self.app))

        ffmpeg_update_stable_action = QAction(self.si(QtWidgets.QStyle.SP_ArrowDown), t("Download Stable FFmpeg"), self)
        ffmpeg_update_stable_action.triggered.connect(self.download_stable_ffmpeg)

        ffmpeg_update_action = QAction(self.si(QtWidgets.QStyle.SP_ArrowDown), t("Download Nightly FFmpeg"), self)
        ffmpeg_update_action.triggered.connect(self.download_ffmpeg)

        clean_logs_action = QAction(self.si(QtWidgets.QStyle.SP_DialogResetButton), t("Clean Old Logs"), self)
        clean_logs_action.triggered.connect(self.clean_old_logs)

        help_menu = menubar.addMenu(t("Help"))
        help_menu.addAction(wiki_action)
        help_menu.addSeparator()

        if changes_file.exists() or local_changes_file.exists() or local_package_changes_file.exists():
            help_menu.addAction(changes_action)
        help_menu.addAction(report_action)
        help_menu.addAction(log_dir_action)
        # help_menu.addAction(log_action)
        help_menu.addAction(clean_logs_action)
        help_menu.addSeparator()
        help_menu.addAction(version_action)
        if reusables.win_based:
            help_menu.addAction(ffmpeg_update_stable_action)
            help_menu.addAction(ffmpeg_update_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

    def show_wiki(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/wiki"))

    def show_concat(self):
        self.concat = ConcatWindow(app=self.app, main=self.main)
        self.concat.show()

    # def show_hdr10p_inject(self):
    #     self.hdr10p_inject = HDR10PlusInjectWindow(app=self.app, main=self.main)
    #     self.hdr10p_inject.show()

    def show_about(self):
        self.about = About(app=self.app)
        self.about.show()

    def show_setting(self):
        self.setting = Settings(self.app, self.main)
        self.setting.show()

    def new_profile(self):
        if not self.app.fastflix.current_video:
            error_message(t("Please load in a video to configure a new profile"))
        else:
            self.main.page_update(build_thumbnail=False)
            if self.profile_window:
                self.profile_window.close()
            self.profile_window = ProfileWindow(self.app, self.main, self)
            self.profile_window.show()

    def show_profile(self):
        self.profile_details = ProfileDetails(
            self.app.fastflix.config.selected_profile, self.app.fastflix.config.profile
        )
        self.profile_details.show()

    def delete_profile(self):
        if self.app.fastflix.config.selected_profile in get_preset_defaults():
            return error_message(
                f"{self.app.fastflix.config.selected_profile} " f"{t('is a default profile and will not be removed')}"
            )
        self.main.loading_video = True
        del self.app.fastflix.config.profiles[self.app.fastflix.config.selected_profile]
        self.app.fastflix.config.selected_profile = "Standard Profile"
        self.app.fastflix.config.save()
        self.main.widgets.profile_box.clear()
        self.main.widgets.profile_box.addItems(self.app.fastflix.config.profiles.keys())
        self.main.loading_video = False
        self.main.widgets.profile_box.setCurrentText("Standard Profile")
        self.main.widgets.convert_to.setCurrentIndex(0)

    # def show_logs(self):
    #     self.logs.show()

    def show_changes(self):
        if not self.changes:
            self.changes = Changes()
        self.changes.show()

    def open_issues(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/cdgriffith/FastFlix/issues"))

    def show_log_dir(self):
        OpenFolder(self, str(self.app.fastflix.log_path)).run()

    def download_stable_ffmpeg(self):
        self.download_ffmpeg(ffmpeg_version="stable")

    def download_ffmpeg(self, ffmpeg_version="latest"):
        ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True)) / "bin"
        ffmpeg = ffmpeg_folder / "ffmpeg.exe"
        ffprobe = ffmpeg_folder / "ffprobe.exe"
        try:
            self.pb = ProgressBar(
                self.app,
                [Task(t("Downloading FFmpeg"), grab_stable_ffmpeg if ffmpeg_version == "stable" else latest_ffmpeg)],
                signal_task=True,
                can_cancel=True,
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

    def clean_old_logs(self, show_errors=True):
        try:
            self.pb = ProgressBar(self.app, [Task(t("Clean Old Logs"), clean_logs)], signal_task=True, can_cancel=False)
        except Exception:
            if show_errors:
                error_message(t("Could not compress old logs"), traceback=True)
        self.pb = None

    def set_stay_top(self):
        if self.app.fastflix.config.stay_on_top:
            # Change to not stay on top
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.stay_on_top_action.setIcon(self.si(QtWidgets.QStyle.SP_DialogNoButton))
        else:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.stay_on_top_action.setIcon(self.si(QtWidgets.QStyle.SP_DialogYesButton))
        self.show()

        self.app.fastflix.config.stay_on_top = not self.app.fastflix.config.stay_on_top
        self.app.fastflix.config.save()

    def open_many(self):
        if self.app.fastflix.current_video:
            discard = yes_no_message(
                f'{t("There is already a video being processed")}<br>' f'{t("Are you sure you want to discard it?")}',
                title="Discard current video",
            )
            if not discard:
                return
        self.main.clear_current_video()
        self.mfw = MultipleFilesWindow(app=self.app, main=self.main)
        self.mfw.show()

        # folder_name = QtWidgets.QFileDialog.getExistingDirectory(self)
        # if not folder_name:
        #     return
        # self.main.open_many(paths=[x for x in Path(folder_name).glob("*") if x.name.lower().endswith(video_file_types)])


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
        # title.setFont(QtGui.QFont(self.app.font().family(), 9, weight=70))
        layout.addWidget(title)
        for k, v in settings.model_dump().items():
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
        # profile_title.setFont(QtGui.QFont(self.app.font().family(), 10, weight=70))
        main_section.addWidget(profile_title)
        for k, v in profile.model_dump().items():
            if k == "advanced_options":
                continue
            if k.lower().startswith("audio") or k.lower() == "profile_version":
                continue
            if k not in setting_types.keys():
                item_1 = QtWidgets.QLabel(t(" ".join(str(k).split("_")).title()))
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

        splitter = QtWidgets.QWidget()
        splitter.setMaximumWidth(1)
        splitter.setStyleSheet("background-color: #999999")
        self.layout.addWidget(splitter)

        advanced_section = QtWidgets.QVBoxLayout(self)
        advanced_section.addWidget(QtWidgets.QLabel(t("Advanced Options")))
        for k, v in profile.advanced_options.model_dump().items():
            if k.endswith("_index"):
                continue
            item_1 = QtWidgets.QLabel(k)
            item_2 = QtWidgets.QLabel(str(v))
            item_2.setMaximumWidth(150)
            inner_layout = QtWidgets.QHBoxLayout()
            inner_layout.addWidget(item_1)
            inner_layout.addWidget(item_2)
            advanced_section.addLayout(inner_layout)
        self.layout.addLayout(advanced_section)

        self.setMinimumWidth(780)
        self.setLayout(self.layout)
