#!/usr/bin/env python
__version__ = '1.0.0'
__author__ = 'Chris Griffith'

name = 'av1'

video_extension = "mkv"
video_width_divisor = 8
video_height_divisor = 8

enable_subtitles = True
enable_audio = True

audio_formats = []

from flix.plugins.av1.command_builder import build
from flix.plugins.av1.settings_panel import AV1 as settings_panel


