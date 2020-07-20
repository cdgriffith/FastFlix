#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = "1.0.0"
__author__ = "Chris Griffith"

name = "GIF"

video_extension = "gif"
video_dimension_divisor = 1

enable_subtitles = False
enable_audio = False

audio_formats = []

from fastflix.plugins.gif.command_builder import build
from fastflix.plugins.gif.settings_panel import GIF as settings_panel
