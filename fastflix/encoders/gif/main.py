#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "GIF"

video_extension = "gif"
video_dimension_divisor = 1
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_gif.png")).resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_concat = True

audio_formats = []

from fastflix.encoders.gif.command_builder import build
from fastflix.encoders.gif.settings_panel import GIF as settings_panel
