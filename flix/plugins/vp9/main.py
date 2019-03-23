#!/usr/bin/env python
__version__ = '1.0.0'
__author__ = 'Chris Griffith'

name = 'vp9'

video_extension = "webm"
video_dimension_divisor = 1

enable_subtitles = True
enable_audio = True

audio_formats = ['libopus',
                 'libvorbis']

from plugins.vp9.command_builder import build
from plugins.vp9.settings_panel import VP9 as settings_panel


