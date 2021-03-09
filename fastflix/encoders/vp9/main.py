#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "VP9"
requires = "libvpx"
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_vp9.png")).resolve())


video_extension = "mkv"
video_dimension_divisor = 2

enable_subtitles = False
enable_audio = True
enable_attachments = False

audio_formats = ["libopus", "libvorbis"]

from fastflix.encoders.vp9.command_builder import build
from fastflix.encoders.vp9.settings_panel import VP9 as settings_panel
