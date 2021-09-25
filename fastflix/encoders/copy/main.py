#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
from fastflix.resources import copy_icon

name = "Copy"

video_extension = "mkv"
video_dimension_divisor = 1
icon = copy_icon

enable_subtitles = True
enable_audio = True
enable_attachments = True


from fastflix.encoders.copy.command_builder import build
from fastflix.encoders.copy.settings_panel import Copy as settings_panel
