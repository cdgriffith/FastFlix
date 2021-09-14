#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from pathlib import Path

import pkg_resources

name = "AVC (NVEncC)"

video_extension = "mkv"
video_dimension_divisor = 1
icon = str(Path(pkg_resources.resource_filename(__name__, f"../../data/encoders/icon_nvencc.png")).resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = False

from fastflix.encoders.nvencc_avc.command_builder import build
from fastflix.encoders.nvencc_avc.settings_panel import NVENCCAVC as settings_panel
