#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional, Union

from pydantic import field_validator, BaseModel, Field
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
    QSVEncCSettings,
    QSVEncCAV1Settings,
    QSVEncCH264Settings,
    NVEncCSettings,
    NVEncCAVCSettings,
    NVEncCAV1Settings,
    VCEEncCAVCSettings,
    VCEEncCSettings,
    VCEEncCAV1Settings,
    HEVCVideoToolboxSettings,
    H264VideoToolboxSettings,
    SVTAVIFSettings,
    VVCSettings,
    VAAPIH264Settings,
    VAAPIHEVCSettings,
    VAAPIVP9Settings,
    VAAPIMPEG2Settings,
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
    match_type: Union[MatchType, list[MatchType]]  # TODO figure out why when saved becomes list in yaml
    match_item: Union[MatchItem, list[MatchType]]
    match_input: str = "*"
    conversion: Optional[str] = None
    bitrate: Optional[str] = None
    downmix: Optional[Union[str, int]] = None

    @field_validator("match_type", mode="before")
    @classmethod
    def match_type_must_be_enum(cls, v):
        if isinstance(v, list):
            return MatchType(v[0])
        return MatchType(v)

    @field_validator("match_item", mode="before")
    @classmethod
    def match_item_must_be_enum(cls, v):
        if isinstance(v, list):
            return MatchType(v[0])
        return MatchItem(v)

    @field_validator("downmix", mode="before")
    @classmethod
    def downmix_as_string(cls, v):
        fixed = {1: "monoo", 2: "stereo", 3: "2.1", 4: "3.1", 5: "5.0", 6: "5.1", 7: "6.1", 8: "7.1"}
        if isinstance(v, str) and v.isnumeric():
            v = int(v)
        if isinstance(v, int):
            if v in fixed:
                return fixed[v]
            return None
        return v

    @field_validator("bitrate", mode="before")
    @classmethod
    def bitrate_k_end(cls, v):
        if v and not v.endswith("k"):
            return f"{v}k"
        return v


class SubtitleMatch(BaseModel):
    match_type: Union[MatchType, list[MatchType]]
    match_item: Union[MatchItem, list[MatchType]]
    match_input: str


class AdvancedOptions(BaseModel):
    video_speed: float = 1
    deblock: Optional[str] = None
    deblock_size: int = 16
    tone_map: str = "hable"
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
    fast_seek: bool = True
    rotate: int = 0
    vertical_flip: bool = False
    horizontal_flip: bool = False
    copy_chapters: bool = True
    remove_metadata: bool = True
    remove_hdr: bool = False
    encoder: str = "HEVC (x265)"
    resolution_method: str = "auto"
    resolution_custom: str | None = None
    output_type: str = ".mkv"

    audio_filters: Optional[list[AudioMatch] | bool] = None
    # subtitle_filters: Optional[list[SubtitleMatch]] = None

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
    vvc: Optional[VVCSettings] = None
    x264: Optional[x264Settings] = None
    rav1e: Optional[rav1eSettings] = None
    svt_av1: Optional[SVTAV1Settings] = None
    svt_av1_avif: Optional[SVTAVIFSettings] = None
    vp9: Optional[VP9Settings] = None
    aom_av1: Optional[AOMAV1Settings] = None
    gif: Optional[GIFSettings] = None
    webp: Optional[WebPSettings] = None
    copy_settings: Optional[CopySettings] = None
    ffmpeg_hevc_nvenc: Optional[FFmpegNVENCSettings] = None
    qsvencc_hevc: Optional[QSVEncCSettings] = None
    qsvencc_av1: Optional[QSVEncCAV1Settings] = None
    qsvencc_avc: Optional[QSVEncCH264Settings] = None
    nvencc_hevc: Optional[NVEncCSettings] = None
    nvencc_avc: Optional[NVEncCAVCSettings] = None
    nvencc_av1: Optional[NVEncCAV1Settings] = None
    vceencc_hevc: Optional[VCEEncCSettings] = None
    vceencc_av1: Optional[VCEEncCAV1Settings] = None
    vceencc_avc: Optional[VCEEncCAVCSettings] = None
    hevc_videotoolbox: Optional[HEVCVideoToolboxSettings] = None
    h264_videotoolbox: Optional[H264VideoToolboxSettings] = None
    vaapi_h264: Optional[VAAPIH264Settings] = None
    vaapi_hevc: Optional[VAAPIHEVCSettings] = None
    vaapi_vp9: Optional[VAAPIVP9Settings] = None
    vaapi_mpeg2: Optional[VAAPIMPEG2Settings] = None
