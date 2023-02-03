#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "HEVC (Video Toolbox)"
requires = "videotoolbox"
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_hevc_toolbox.png")).resolve())


video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 2

enable_subtitles = False
enable_audio = True
enable_attachments = False
enable_concat = True

from fastflix.encoders.hevc_videotoolbox.command_builder import build
from fastflix.encoders.hevc_videotoolbox.settings_panel import HEVCVideoToolbox as settings_panel
