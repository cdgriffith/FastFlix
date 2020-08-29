# -*- coding: utf-8 -*-
import logging

from qtpy import QtWidgets, QtCore, QtGui

__all__ = ["Logs"]

logger = logging.getLogger("fastflix")


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__()
        self.widget = QtWidgets.QTextBrowser(parent)
        self.widget.setReadOnly(True)
        self.widget.setDisabled(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)

    def write(self, m):
        pass


class Logs(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Logs, self).__init__(parent)

        self.setMinimumSize(800, 600)
        layout = QtWidgets.QVBoxLayout()
        log_text_box = QPlainTextEditLogger(self)
        log_text_box.setFormatter(logging.Formatter("<b>%(levelname)s</b> - %(asctime)s - %(message)s"))
        log_text_box.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_text_box)

        log_text_box.setLevel(logging.DEBUG)
        layout.addWidget(QtWidgets.QLabel("Log window scrolling bug causing crashes, currently disabled for safety"))
        layout.addWidget(log_text_box.widget)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.hide()
        # event.accept()
