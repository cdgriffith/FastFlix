# -*- coding: utf-8 -*-
import os
import sys
import importlib.machinery

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # noinspection PyUnresolvedReferences
    base_path = sys._MEIPASS
    pyinstaller = True
except AttributeError:
    base_path = os.path.abspath(".")
    pyinstaller = False


from qtpy import QtWidgets, QtCore, QtGui

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

main_width = 800


def message(msg, parent=None):
    sm = QtWidgets.QMessageBox()
    sm.setText(msg)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.exec_()


def error_message(msg, details=None, traceback=False, parent=None):
    em = QtWidgets.QMessageBox()
    em.setText(msg)
    if details:
        em.setDetailedText(details)
    elif traceback:
        import traceback

        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Ok)
    em.exec_()
