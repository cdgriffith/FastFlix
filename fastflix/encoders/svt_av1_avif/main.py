#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "AVIF (SVT AV1)"
requires = "libsvtav1"

video_extensions = [".avif", ".avis", ".avifs"]
video_dimension_divisor = 8

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_svt_av1.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())


enable_subtitles = True
enable_audio = False
enable_attachments = False
enable_concat = True

from fastflix.encoders.svt_av1_avif.command_builder import build
from fastflix.encoders.svt_av1_avif.settings_panel import SVT_AV1_AVIF as settings_panel
