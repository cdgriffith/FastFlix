#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "H264 (Video Toolbox)"
requires = "videotoolbox"
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_h264_toolbox.png")).resolve())


video_extension = "mkv"
video_dimension_divisor = 2

enable_subtitles = False
enable_audio = True
enable_attachments = False
enable_concat = True

from fastflix.encoders.h264_videotoolbox.command_builder import build
from fastflix.encoders.h264_videotoolbox.settings_panel import H264VideoToolbox as settings_panel
