# -*- coding: utf-8 -*-
import logging

from PySide6 import QtWidgets


__all__ = ["AudioSelect"]

logger = logging.getLogger("fastflix")


class AudioSelect(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self.main = parent
