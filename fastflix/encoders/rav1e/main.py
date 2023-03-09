#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "AV1 (rav1e)"
requires = "librav1e"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 8

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_rav1e.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.rav1e.command_builder import build
from fastflix.encoders.rav1e.settings_panel import RAV1E as settings_panel
