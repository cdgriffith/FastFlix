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

if os.getenv('SHIBOKEN2') and os.getenv('PYSIDE2'):
    # This is required to keep LGPL libraries truly dynamically linked when built into a binary
    importlib.machinery.SourceFileLoader('shiboken2', os.getenv('SHIBOKEN2')).load_module()
    PySide2 = importlib.machinery.SourceFileLoader('PySide2', os.getenv('PYSIDE2')).load_module()

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2 import __version__ as pyside_version


def message(msg, parent=None):
    sm = QtWidgets.QMessageBox(parent=parent)
    sm.setText(msg)
    sm.setStandardButtons(QtWidgets.QMessageBox.Ok)
    sm.exec_()


def error_message(msg, details=None, traceback=False, parent=None):
    em = QtWidgets.QMessageBox(parent=parent)
    em.setText(msg)
    if details:
        em.setDetailedText(details)
    elif traceback:
        import traceback
        em.setDetailedText(traceback.format_exc())
    em.setStandardButtons(QtWidgets.QMessageBox.Ok)
    em.exec_()

