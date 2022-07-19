#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AVIF (SVT AV1)"
requires = "libsvtav1"

video_extension = "avif"
video_dimension_divisor = 8
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_svt_av1.png")).resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_concat = True

from fastflix.encoders.svt_av1_avif.command_builder import build
from fastflix.encoders.svt_av1_avif.settings_panel import SVT_AV1_AVIF as settings_panel
