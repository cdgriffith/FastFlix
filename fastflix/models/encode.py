# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class AudioTrack(BaseModel):
    index: int
    outdex: int
    codec: str = ""
    downmix: int = 0
    title: str = ""
    language: str = ""
    conversion_bitrate: str = ""
    conversion_codec: str = ""


class SubtitleTrack(BaseModel):
    index: int
    outdex: int
    disposition: Optional[str] = ""
    burn_in: bool = False
    language: str = ""
    subtitle_type: str = ""


class AttachmentTrack(BaseModel):
    outdex: int
    index: Optional[int] = None
    attachment_type: str = "cover"
    file_path: Optional[Path] = None
    filename: Optional[str] = None


class EncoderSettings(BaseModel):
    max_muxing_queue_size: str = "1024"
    pix_fmt: str = "yuv420p10le"
    extra: str = ""
    extra_both_passes: bool = False


class x265Settings(EncoderSettings):
    name = "HEVC (x265)"  # MUST match encoder main.name
    preset: str = "medium"
    intra_encoding: bool = False
    profile: str = "default"
    tune: str = "default"
    hdr10: bool = False
    hdr10_opt: bool = False
    dhdr10_opt: bool = False
    repeat_headers: bool = False
    aq_mode: int = 2
    hdr10plus_metadata: str = ""
    crf: Optional[int] = 22
    bitrate: Optional[str] = None
    x265_params: List[str] = Field(default_factory=list)
    bframes: int = 4
    lossless: bool = False
    b_adapt: int = 2
    intra_refresh: bool = False
    intra_smoothing: bool = True
    frame_threads: int = 0


class x264Settings(EncoderSettings):
    name = "AVC (x264)"
    preset: str = "medium"
    profile: str = "default"
    tune: Optional[str] = None
    pix_fmt: str = "yuv420p"
    crf: Optional[int] = 23
    bitrate: Optional[str] = None


class rav1eSettings(EncoderSettings):
    name = "AV1 (rav1e)"
    speed: str = "-1"
    tile_columns: str = "-1"
    tile_rows: str = "-1"
    tiles: str = "0"
    single_pass: bool = False
    qp: Optional[int] = 24
    bitrate: Optional[str] = None


class SVTAV1Settings(EncoderSettings):
    name = "AV1 (SVT AV1)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    tier: str = "main"
    # scene_detection: str = "false"
    single_pass: bool = False
    speed: str = "7"
    qp: Optional[int] = 24
    bitrate: Optional[str] = None


class VP9Settings(EncoderSettings):
    name = "VP9"
    profile: int = 2
    quality: str = "good"
    speed: str = "0"
    row_mt: int = 0
    single_pass: bool = False
    crf: Optional[int] = 31
    bitrate: Optional[str] = None


class AOMAV1Settings(EncoderSettings):
    name = "AV1 (AOM)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    usage: str = "good"
    row_mt: str = "enabled"
    cpu_used: str = "4"
    crf: Optional[int] = 26
    bitrate: Optional[str] = None


class WebPSettings(EncoderSettings):
    name = "WebP"
    lossless: str = "0"
    compression: str = "3"
    preset: str = "none"
    qscale: int = 15


class GIFSettings(EncoderSettings):
    name = "GIF"
    fps: int = 15
    dither: str = "sierra2_4a"


class CopySettings(EncoderSettings):
    name = "Copy"
