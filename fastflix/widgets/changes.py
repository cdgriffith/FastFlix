# -*- coding: utf-8 -*-
import logging
import re

import mistune
from PySide6 import QtCore, QtWidgets

from fastflix.resources import changes_file, local_changes_file, local_package_changes_file

__all__ = ["Changes"]

logger = logging.getLogger("fastflix")


issues = re.compile(r"\s(#\d+)\s")


class Changes(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        content = QtWidgets.QWidget(self)
        self.setWidget(content)
        lay = QtWidgets.QVBoxLayout(content)

        if changes_file.exists():
            content = changes_file.read_text(encoding="utf-8", errors="ignore")
        elif local_package_changes_file.exists():
            content = local_package_changes_file.read_text(encoding="utf-8", errors="ignore")
        else:
            if not local_changes_file.exists():
                raise Exception("Could not locate changlog file")
            content = local_changes_file.read_text(encoding="utf-8", errors="ignore")

        linked_content = issues.sub(
            " <a href='https://github.com/cdgriffith/FastFlix/issues/\\1' style='color: black' >\\1</a> ", content
        ).replace("issues/#", "issues/")

        self.label = QtWidgets.QLabel(mistune.html(linked_content))
        self.label.setOpenExternalLinks(True)

        # setting alignment to the text
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)

    def closeEvent(self, event):
        self.hide()
        # event.accept()
