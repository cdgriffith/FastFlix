#!/usr/bin/env python
__version__ = '1.0.0'
__author__ = 'Chris Griffith'

name = 'gif'

video_extension = "gif"
video_dimension_divisor = 1

enable_subtitles = False
enable_audio = False

audio_formats = []

from plugins.gif.command_builder import build
from plugins.gif.settings_panel import GIF as settings_panel


