#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "AVC (x264)"
requires = "libx264"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_x264.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.avc_x264.command_builder import build
from fastflix.encoders.avc_x264.settings_panel import AVC as settings_panel
