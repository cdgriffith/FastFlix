# -*- coding: utf-8 -*-
import importlib.machinery
import os
import sys
from datetime import datetime
from distutils.version import StrictVersion
from pathlib import Path

import pkg_resources
import requests

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


def latest_ffmpeg(no_new_dialog=False):
    from fastflix.version import __version__

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases/latest"
    data = requests.get(url).json()
    if data["tag_name"] != __version__ and StrictVersion(data["tag_name"]) > StrictVersion(__version__):
        for asset in data["assets"]:
            if asset["name"].endswith("win64.zip"):
                link = asset["browser_download_url"]
                break
        else:
            if no_new_dialog:
                message("You are using the latest version of FastFlix")
            return
        message(
            f"There is a newer version of FastFlix available! <br> "
            f"<a href='{link}'>Download FastFlix {data['tag_name']} now</a>",
            title="New Version",
        )
        return
    if no_new_dialog:
        message("You are using the latest version of FastFlix")


def file_date():
    return datetime.now().isoformat().replace(":", ".").rsplit(".", 1)[0]
