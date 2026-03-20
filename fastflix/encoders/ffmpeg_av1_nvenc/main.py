#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "AV1 (NVENC)"
requires = "cuda-llvm"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v", ".webm"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / "data/encoders/icon_nvenc.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True
enable_data = True

from fastflix.encoders.ffmpeg_av1_nvenc.command_builder import build  # noqa: F401,E402
from fastflix.encoders.ffmpeg_av1_nvenc.settings_panel import AV1NVENC as settings_panel  # noqa: F401,E402
