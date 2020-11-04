# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union
from tempfile import TemporaryDirectory

from appdirs import user_data_dir
from box import Box

from fastflix.models.base import BaseDataClass


@dataclass
class VideoSettings(BaseDataClass):
    crop: str = None
    end_time: Union[float, int] = None
    start_time: Union[float, int] = 0
    fast_seek: bool = True
    rotate: str = None
    vertical_flip: bool = False
    horizontal_flip: bool = False
    remove_metadata: bool = True
    copy_chapters: bool = True
    video_title: str = None
    selected_track: int = 0


@dataclass
class Video(BaseDataClass):
    source: Path
    width: int = 0
    height: int = 0
    duration: Union[float, int] = 0

    output_path: Path = None
    streams: Box = None
    bit_depth: int = 8
    video_settings: VideoSettings = field(default_factory=lambda: VideoSettings())
    work_path: TemporaryDirectory = None
    pix_fmt: str = ""
    format: Box = None

    # HDR10 Details
    color_space: str = ""
    color_primaries: str = ""
    color_transfer: str = ""
    master_display: Box = None
    cll: str = ""
