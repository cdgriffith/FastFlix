#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "GIF"

video_extensions = [".gif"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_gif.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = False
enable_audio = False
enable_attachments = False
enable_concat = False

audio_formats = []

from fastflix.encoders.gif.command_builder import build
from fastflix.encoders.gif.settings_panel import GIF as settings_panel
