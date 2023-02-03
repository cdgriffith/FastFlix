#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "HEVC (x265)"
requires = "libx265"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 1
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_x265.png")).resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.hevc_x265.command_builder import build
from fastflix.encoders.hevc_x265.settings_panel import HEVC as settings_panel
