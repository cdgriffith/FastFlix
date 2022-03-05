#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Optional, Union, Dict

from pydantic import BaseModel, Field, validator
from box import Box
from enum import Enum

from fastflix.models.encode import (
    AOMAV1Settings,
    CopySettings,
    GIFSettings,
    FFmpegNVENCSettings,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    NVEncCSettings,
    NVEncCAVCSettings,
    VCEEncCAVCSettings,
    VCEEncCSettings,
)

__all__ = ["MatchItem", "MatchType", "AudioMatch", "Profile", "SubtitleMatch", "AdvancedOptions"]


class MatchItem(Enum):
    ALL = 1
    TITLE = 2
    TRACK = 3
    LANGUAGE = 4
    CHANNELS = 5


class MatchType(Enum):
    ALL = 1
    FIRST = 2
    LAST = 3


class AudioMatch(BaseModel):
    match_type: Union[MatchType, List[MatchType]]  # TODO figure out why when saved becomes list in yaml
    match_item: Union[MatchItem, List[MatchType]]
    match_input: str
    conversion: Optional[str] = None
    bitrate: str
    downmix: int

    @validator("match_type")
    def match_type_must_be_enum(cls, v):
        if isinstance(v, list):
            return MatchType(v[0])
        return MatchType(v)

    @validator("match_item")
    def match_item_must_be_enum(cls, v):
        if isinstance(v, list):
            return MatchType(v[0])
        return MatchItem(v)


class SubtitleMatch(BaseModel):
    match_type: Union[MatchType, List[MatchType]]
    match_item: Union[MatchItem, List[MatchType]]
    match_input: str


# TODO upgrade path from old profile to new profile


class AdvancedOptions(BaseModel):
    video_speed: float = 1
    deblock: Optional[str] = None
    deblock_size: int = 16
    tone_map: Optional[str] = None
    vsync: Optional[str] = None
    brightness: Optional[str] = None
    saturation: Optional[str] = None
    contrast: Optional[str] = None
    maxrate: Optional[int] = None
    bufsize: Optional[int] = None
    source_fps: Optional[str] = None
    output_fps: Optional[str] = None
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    denoise: Optional[str] = None
    denoise_type_index: int = 0
    denoise_strength_index: int = 0


class Profile(BaseModel):
    profile_version: Optional[int] = 1
    auto_crop: bool = False
    keep_aspect_ratio: bool = True
    fast_seek: bool = True
    rotate: int = 0
    vertical_flip: bool = False
    horizontal_flip: bool = False
    copy_chapters: bool = True
    remove_metadata: bool = True
    remove_hdr: bool = False
    encoder: str = "HEVC (x265)"

    audio_filters: Optional[List[AudioMatch]] = None
    # subtitle_filters: Optional[List[SubtitleMatch]] = None

    # Legacy Audio, here to properly import old profiles
    audio_language: Optional[str] = None
    audio_select: Optional[bool] = None
    audio_select_preferred_language: Optional[bool] = None
    audio_select_first_matching: Optional[bool] = None

    subtitle_language: Optional[str] = None
    subtitle_select: Optional[bool] = None
    subtitle_select_preferred_language: Optional[bool] = None
    subtitle_automatic_burn_in: Optional[bool] = None
    subtitle_select_first_matching: Optional[bool] = None

    advanced_options: AdvancedOptions = Field(default_factory=AdvancedOptions)

    x265: Optional[x265Settings] = None
    x264: Optional[x264Settings] = None
    rav1e: Optional[rav1eSettings] = None
    svt_av1: Optional[SVTAV1Settings] = None
    vp9: Optional[VP9Settings] = None
    aom_av1: Optional[AOMAV1Settings] = None
    gif: Optional[GIFSettings] = None
    webp: Optional[WebPSettings] = None
    copy_settings: Optional[CopySettings] = None
    ffmpeg_hevc_nvenc: Optional[FFmpegNVENCSettings] = None
    nvencc_hevc: Optional[NVEncCSettings] = None
    nvencc_avc: Optional[NVEncCAVCSettings] = None
    vceencc_hevc: Optional[VCEEncCSettings] = None
    vceencc_avc: Optional[VCEEncCAVCSettings] = None
