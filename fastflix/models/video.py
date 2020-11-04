# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union, List
from tempfile import TemporaryDirectory

from appdirs import user_data_dir
from box import Box

from fastflix.models.base import BaseDataClass

from fastflix.models.encode import AudioTrack, SubtitleTrack


@dataclass
class VideoSettings(BaseDataClass):
    crop: Union[str, None] = None
    start_time: Union[float, int] = 0
    end_time: Union[float, int] = 0
    fast_seek: bool = True
    rotate: Union[str, None] = None
    vertical_flip: bool = False
    horizontal_flip: bool = False
    remove_metadata: bool = True
    copy_chapters: bool = True
    video_title: str = ""
    selected_track: int = 0
    output_path: Path = None
    pix_fmt: str = ""
    scale: Union[str, None] = None
    encoder_options: Box = field(default_factory=Box)
    audio_tracks: List[AudioTrack] = field(default_factory=list)
    subtitle_tracks: List[SubtitleTrack] = field(default_factory=list)


@dataclass
class Video(BaseDataClass):
    source: Path
    width: int = 0
    height: int = 0
    duration: Union[float, int] = 0
    streams: Box = None
    bit_depth: int = 8
    video_settings: VideoSettings = field(default_factory=lambda: VideoSettings())
    work_path: TemporaryDirectory = None
    pix_fmt: str = ""
    format: Box = None

    # Color Range Details
    color_space: str = ""
    color_primaries: str = ""
    color_transfer: str = ""

    # HDR10 Details
    master_display: Box = None
    cll: str = ""
