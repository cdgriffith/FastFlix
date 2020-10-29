# -*- coding: utf-8 -*-
from pathlib import Path
from dataclasses import dataclass
from typing import Union, Any

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


@dataclass
class Video(BaseDataClass):
    source: Path
    width: int
    height: int
    duration: Union[float, int]
    colorspace: str = None
    output_path: Path = None
    streams: dict = None
    bit_depth: int = 8
    video_settings: VideoSettings = None
