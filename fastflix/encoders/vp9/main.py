#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "VP9"
requires = "libvpx"


video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 2

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_vp9.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = True
enable_attachments = False
enable_concat = True

from fastflix.encoders.vp9.command_builder import build
from fastflix.encoders.vp9.settings_panel import VP9 as settings_panel
