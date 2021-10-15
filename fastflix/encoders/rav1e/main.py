#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AV1 (rav1e)"
requires = "librav1e"

video_extension = "mkv"
video_dimension_divisor = 8
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_rav1e.png")).resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.rav1e.command_builder import build
from fastflix.encoders.rav1e.settings_panel import RAV1E as settings_panel
