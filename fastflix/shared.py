# -*- coding: utf-8 -*-
import importlib.machinery
import os
import sys
from pathlib import Path

import pkg_resources

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


def message(msg):
    sm = QtWidgets.QMessageBox()
    sm.setText(msg)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.setWindowIcon(icon)
    sm.exec_()


def error_message(msg, details=None, traceback=False):
    em = MyMessageBox()
    em.setText(msg)
    em.setWindowIcon(icon)
    if details:
        em.setInformativeText(details)
    elif traceback:
        import traceback

        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Close)
    em.exec_()
