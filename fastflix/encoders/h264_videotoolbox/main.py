#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "H264 (Video Toolbox)"
requires = "videotoolbox"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 2

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_h264_toolbox.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = True
enable_attachments = False
enable_concat = True

from fastflix.encoders.h264_videotoolbox.command_builder import build
from fastflix.encoders.h264_videotoolbox.settings_panel import H264VideoToolbox as settings_panel
