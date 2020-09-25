# -*- coding: utf-8 -*-
import logging
from pathlib import Path

import mistune
from qtpy import QtCore, QtGui, QtWidgets

__all__ = ["Changes"]

logger = logging.getLogger("fastflix")

markdown = mistune.Markdown()


class Changes(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        content = QtWidgets.QWidget(self)
        self.setWidget(content)
        lay = QtWidgets.QVBoxLayout(content)

        changes_files = Path(__file__).parent.parent / "CHANGES"
        if not changes_files.exists():
            changes_files = Path(__file__).parent.parent.parent / "CHANGES"
            if not changes_files.exists():
                raise Exception("Could not locate changlog file")

        self.label = QtWidgets.QLabel(markdown((changes_files.read_text())))

        # setting alignment to the text
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)

    def closeEvent(self, event):
        self.hide()
        # event.accept()
