# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional
import secrets

from PySide6 import QtWidgets, QtCore, QtGui

from fastflix.flix import (
    generate_thumbnail_command,
)
from fastflix.encoders.common import helpers
from fastflix.resources import get_icon
from fastflix.language import t

__all__ = ["AudioSelect"]

logger = logging.getLogger("fastflix")


class AudioSelect(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self.main = parent
