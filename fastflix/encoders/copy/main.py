#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "Copy"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v", ".gif", ".avif", ".webp"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / "data/icons/black/onyx-copy.svg"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True


from fastflix.encoders.copy.command_builder import build
from fastflix.encoders.copy.settings_panel import Copy as settings_panel
