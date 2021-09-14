#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AVC (VCEEncC)"

video_extension = "mkv"
video_dimension_divisor = 1
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_vceencc.png")).resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = False

from fastflix.encoders.vceencc_avc.command_builder import build
from fastflix.encoders.vceencc_avc.settings_panel import VCEENCCAVC as settings_panel
