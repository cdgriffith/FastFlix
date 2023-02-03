#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AV1 (SVT AV1)"
requires = "libsvtav1"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".webm", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 8
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_svt_av1.png")).resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.svt_av1.command_builder import build
from fastflix.encoders.svt_av1.settings_panel import SVT_AV1 as settings_panel
