#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "WebP"

requires = "libwebp"
video_extensions = [".webp"]
video_dimension_divisor = 2

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_webp.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_concat = True

audio_formats = []

from fastflix.encoders.webp.command_builder import build
from fastflix.encoders.webp.settings_panel import WEBP as settings_panel
