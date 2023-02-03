#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "WebP"

requires = "libwebp"
video_extension = ["webp"]
video_dimension_divisor = 2
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_webp.png")).resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_concat = True

audio_formats = []

from fastflix.encoders.webp.command_builder import build
from fastflix.encoders.webp.settings_panel import WEBP as settings_panel
