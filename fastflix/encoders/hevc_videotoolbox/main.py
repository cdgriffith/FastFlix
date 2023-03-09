#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "HEVC (Video Toolbox)"
requires = "videotoolbox"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 2

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_hevc_toolbox.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = True
enable_attachments = False
enable_concat = True

from fastflix.encoders.hevc_videotoolbox.command_builder import build
from fastflix.encoders.hevc_videotoolbox.settings_panel import HEVCVideoToolbox as settings_panel
