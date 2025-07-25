#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "HEVC (x265)"
requires = "libx265"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / "data/encoders/icon_x265.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.hevc_x265.command_builder import build  # noqa: F401,E402
from fastflix.encoders.hevc_x265.settings_panel import HEVC as settings_panel  # noqa: F401,E402
