#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "Modify"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v", ".gif", ".avif", ".webp"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / "data/icons/black/onyx-advanced.svg"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_advanced = False

from fastflix.encoders.modify.command_builder import build
from fastflix.encoders.modify.settings_panel import Modify as settings_panel
