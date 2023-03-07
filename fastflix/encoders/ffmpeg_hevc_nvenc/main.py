#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Chris Griffith"
import importlib.resources

name = "HEVC (NVENC)"
requires = "cuda-llvm"

video_extensions = [".mkv", ".mp4", ".ts", ".mov", ".avi", ".mts", ".m2ts", ".m4v"]
video_dimension_divisor = 1

ref = importlib.resources.files("fastflix") / f"data/encoders/icon_nvenc.png"
with importlib.resources.as_file(ref) as icon_file:
    icon = str(icon_file.resolve())

enable_subtitles = True
enable_audio = True
enable_attachments = True
enable_concat = True

from fastflix.encoders.ffmpeg_hevc_nvenc.command_builder import build
from fastflix.encoders.ffmpeg_hevc_nvenc.settings_panel import NVENC as settings_panel
