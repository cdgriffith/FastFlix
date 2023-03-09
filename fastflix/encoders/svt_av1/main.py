#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "AV1 (SVT AV1)"
requires = "libsvtav1"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 8

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_svt_av1.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.svt_av1.command_builder import build
from fastflix.encoders.svt_av1.settings_panel import SVT_AV1 as settings_panel
