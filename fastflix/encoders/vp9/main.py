#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"

name = "VP9"
requires = "libvpx"

video_extension = "webm"
video_dimension_divisor = 1

enable_subtitles = True
enable_audio = True
enable_attachments = True

audio_formats = ["libopus", "libvorbis"]

from fastflix.encoders.vp9.command_builder import build
from fastflix.encoders.vp9.settings_panel import VP9 as settings_panel
