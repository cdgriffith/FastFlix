#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AV1 (AOM)"
requires = "libaom"
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_av1_aom.png")).resolve())

video_extension = "mkv"
video_dimension_divisor = 8

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.av1_aom.command_builder import build
from fastflix.encoders.av1_aom.settings_panel import AV1 as settings_panel
