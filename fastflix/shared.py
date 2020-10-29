# -*- coding: utf-8 -*-
import importlib.machinery
import shutil
import logging
import os
import sys
from datetime import datetime
from distutils.version import StrictVersion
from pathlib import Path
from threading import Thread

import pkg_resources
import requests
import reusables
from appdirs import user_data_dir

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # noinspection PyUnresolvedReferences
    base_path = sys._MEIPASS
    pyinstaller = True
except AttributeError:
    base_path = os.path.abspath(".")
    pyinstaller = False

from qtpy import QtCore, QtGui, QtWidgets

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

main_width = 800

my_data = str(Path(pkg_resources.resource_filename(__name__, f"../data/icon.ico")).resolve())
icon = QtGui.QIcon(my_data)

logger = logging.getLogger("fastflix")


class MyMessageBox(QtWidgets.QMessageBox):
    def __init__(self):
        QtWidgets.QMessageBox.__init__(self)
        self.setSizeGripEnabled(True)

    def event(self, e):
        result = QtWidgets.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        textEdit = self.findChild(QtWidgets.QTextEdit)
        if textEdit is not None:
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        return result


def message(msg, title=None):
    sm = QtWidgets.QMessageBox()
    sm.setText(msg)
    if title:
        sm.setWindowTitle(title)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.setWindowIcon(icon)
    sm.exec_()


def error_message(msg, details=None, traceback=False, title=None):
    em = MyMessageBox()
    em.setText(msg)
    em.setWindowIcon(icon)
    if title:
        em.setWindowTitle(title)
    if details:
        em.setInformativeText(details)
    elif traceback:
        import traceback

        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Close)
    em.exec_()


def latest_ffmpeg(signal, **_):
    ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))
    ffmpeg_folder.mkdir(exist_ok=True)
    url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"

    try:
        data = requests.get(url, timeout=15).json()
    except Exception:
        message("Could not connect to github to check for newer versions.")
        raise

    gpl_ffmpeg = [asset for asset in data["assets"] if asset["name"].endswith("win64-gpl.zip")]
    if not gpl_ffmpeg:
        message(
            "Could not find any matching FFmpeg ending with 'win64-gpl.zip' with "
            "latest release from <a href='https://github.com/BtbN/FFmpeg-Builds/releases/'>"
            "https://github.com/BtbN/FFmpeg-Builds/releases/</a> "
        )
        raise

    req = requests.get(gpl_ffmpeg[0]["browser_download_url"], stream=True)

    filename = ffmpeg_folder / "ffmpeg-full.zip"
    with open(filename, "wb") as f:
        for i, block in enumerate(req.iter_content(chunk_size=1024)):
            if i % 1000 == 0.0:
                # logger.debug(f"Downloaded {i // 1000}MB")
                signal.emit(int(((i * 1024) / gpl_ffmpeg[0]["size"]) * 90))
            f.write(block)

    if filename.stat().st_size < 1000:
        message("FFmpeg was not properly downloaded as the file size is too small")
        try:
            Path(filename).unlink()
        except OSError:
            pass
        raise

    try:
        reusables.extract(filename, path=ffmpeg_folder)
    except Exception:
        message(f"Could not extract FFmpeg files from {filename}!")
        raise

    signal.emit(95)

    try:
        shutil.rmtree(str(ffmpeg_folder / "bin"), ignore_errors=True)
        shutil.rmtree(str(ffmpeg_folder / "doc"), ignore_errors=True)
        Path(filename).unlink()
    except OSError:
        pass

    signal.emit(96)
    sub_dir = next(Path(ffmpeg_folder).glob("ffmpeg-*"))

    for item in os.listdir(sub_dir):
        try:
            shutil.move(str(sub_dir / item), str(ffmpeg_folder))
        except Exception as err:
            message(f"Error while moving files in {ffmpeg_folder}: {err}")
            raise
    signal.emit(98)
    shutil.rmtree(sub_dir, ignore_errors=True)
    signal.emit(100)
    # if done_alert:
    #     message(f"FFmpeg has been downloaded to {ffmpeg_folder}")


def latest_fastflix(no_new_dialog=False):
    from fastflix.version import __version__

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases/latest"
    try:
        data = requests.get(url, timeout=15 if no_new_dialog else 3).json()
    except Exception:
        logger.warning("Could not connect to github to check for newer versions.")
        if no_new_dialog:
            message("Could not connect to github to check for newer versions.")
        return

    if data["tag_name"] != __version__ and StrictVersion(data["tag_name"]) > StrictVersion(__version__):
        portable, installer = None, None
        for asset in data["assets"]:
            if asset["name"].endswith("win64.zip"):
                portable = asset["browser_download_url"]
            if asset["name"].endswith("installer.exe"):
                installer = asset["browser_download_url"]

        download_link = ""
        if installer:
            download_link += f"<a href='{installer}'>Download FastFlix installer {data['tag_name']}</a><br>"
        if portable:
            download_link += f"<a href='{portable}'>Download FastFlix portable {data['tag_name']}</a><br>"
        if (not portable and not installer) or not reusables.win_based:
            html_link = data["html_url"]
            download_link = f"<a href='{html_link}'>View FastFlix {data['tag_name']} now</a>"
        message(
            f"There is a newer version of FastFlix available! <br> {download_link}",
            title="New Version",
        )
        return
    if no_new_dialog:
        message("You are using the latest version of FastFlix")


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".", 1)[0]


CONTINUOUS = 0x80000000
SYSTEM_REQUIRED = 0x00000001


def prevent_sleep_mode():
    """https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx"""
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS | SYSTEM_REQUIRED)
        except Exception:
            logger.exception("Could not prevent system from possibly going to sleep during conversion")
        else:
            logger.debug("System has been asked to not sleep")


def allow_sleep_mode():
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS)
        except Exception:
            logger.exception("Could not allow system to resume sleep mode")
        else:
            logger.debug("System has been allowed to enter sleep mode again")


class FastFlixError(Exception):
    """Generic FastFlixError"""


class FastFlixInternalException(FastFlixError):
    """This should always be caught and never seen by user"""
