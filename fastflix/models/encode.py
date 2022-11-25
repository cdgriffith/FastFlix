#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field
from box import Box


class AudioTrack(BaseModel):
    index: int
    outdex: int
    codec: str = ""
    downmix: Optional[str] = None
    title: str = ""
    language: str = ""
    conversion_bitrate: str = ""
    conversion_codec: str = ""
    profile: Optional[str] = None
    enabled: bool = True
    original: bool = False
    channels: int = 2
    friendly_info: str = ""
    raw_info: Optional[Union[dict, Box]] = None


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
    crf: Optional[Union[int, float]] = 22
    bitrate: Optional[str] = None
    x265_params: list[str] = Field(default_factory=list)
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
    crf: Optional[Union[int, float]] = 23
    bitrate: Optional[str] = None


class FFmpegNVENCSettings(EncoderSettings):
    name = "HEVC (NVENC)"
    preset: str = "slow"
    profile: str = "main"
    tune: str = "hq"
    pix_fmt: str = "p010le"
    bitrate: Optional[str] = "6000k"
    qp: Optional[str] = None
    cq: int = 0
    spatial_aq: int = 0
    rc_lookahead: int = 0
    rc: Optional[str] = None
    tier: str = "main"
    level: Optional[str] = None
    gpu: int = -1
    b_ref_mode: str = "disabled"


class NVEncCSettings(EncoderSettings):
    name = "HEVC (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    aq: str = "off"
    aq_strength: int = 0
    lookahead: Optional[int] = None
    tier: str = "high"
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    multipass: str = "2pass-full"
    mv_precision: str = "Auto"
    init_q_i: Optional[str] = None
    init_q_p: Optional[str] = None
    init_q_b: Optional[str] = None
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    vbr_target: Optional[str] = None
    b_frames: Optional[str] = None
    b_ref_mode: str = "disabled"
    ref: Optional[str] = None
    metrics: bool = False
    force_ten_bit: bool = False


class NVEncCAV1Settings(EncoderSettings):
    name = "AV1 (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    aq: str = "off"
    aq_strength: int = 0
    lookahead: Optional[int] = None
    tier: str = "high"
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    multipass: str = "2pass-full"
    mv_precision: str = "Auto"
    init_q_i: Optional[str] = None
    init_q_p: Optional[str] = None
    init_q_b: Optional[str] = None
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    vbr_target: Optional[str] = None
    b_frames: Optional[str] = None
    b_ref_mode: str = "disabled"
    ref: Optional[str] = None
    metrics: bool = False
    force_ten_bit: bool = False


class QSVEncCSettings(EncoderSettings):
    name = "HEVC (QSVEncC)"
    preset: str = "best"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    lookahead: Optional[str] = None
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    b_frames: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    force_ten_bit: bool = False


class QSVEncCAV1Settings(EncoderSettings):
    name = "AV1 (QSVEncC)"
    preset: str = "best"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    lookahead: Optional[str] = None
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    b_frames: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    force_ten_bit: bool = False


class QSVEncCH264Settings(EncoderSettings):
    name = "AVC (QSVEncC)"
    preset: str = "best"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    lookahead: Optional[str] = None
    level: Optional[str] = None
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    b_frames: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    force_ten_bit: bool = False


class NVEncCAVCSettings(EncoderSettings):
    name = "AVC (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    aq: str = "off"
    aq_strength: int = 0
    lookahead: Optional[int] = None
    tier: str = "high"
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    multipass: str = "2pass-full"
    mv_precision: str = "Auto"
    init_q_i: Optional[str] = None
    init_q_p: Optional[str] = None
    init_q_b: Optional[str] = None
    min_q_i: Optional[str] = None
    min_q_p: Optional[str] = None
    min_q_b: Optional[str] = None
    max_q_i: Optional[str] = None
    max_q_p: Optional[str] = None
    max_q_b: Optional[str] = None
    vbr_target: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    b_frames: Optional[str] = None
    b_ref_mode: str = "disabled"


class VCEEncCSettings(EncoderSettings):
    name = "HEVC (VCEEncC)"
    preset: str = "slow"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    tier: str = "high"
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    mv_precision: str = "q-pel"
    min_q: Optional[str] = None
    max_q: Optional[str] = None
    vbr_target: Optional[str] = None
    b_frames: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    pre_encode: bool = False
    pre_analysis: bool = False
    vbaq: bool = False
    decoder: str = "Hardware"


class VCEEncCAVCSettings(EncoderSettings):
    name = "AVC (VCEEncC)"
    preset: str = "slow"
    profile: str = "Auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[str] = None
    tier: str = "high"
    level: Optional[str] = None
    hdr10plus_metadata: str = ""
    mv_precision: str = "q-pel"
    min_q: Optional[str] = None
    max_q: Optional[str] = None
    b_frames: Optional[str] = None
    ref: Optional[str] = None
    metrics: bool = False
    pre_encode: bool = False
    pre_analysis: bool = False
    vbaq: bool = False
    decoder: str = "Hardware"


class rav1eSettings(EncoderSettings):
    name = "AV1 (rav1e)"
    speed: str = "-1"
    tile_columns: str = "-1"
    tile_rows: str = "-1"
    tiles: str = "0"
    single_pass: bool = False
    qp: Optional[Union[int, float]] = 24
    bitrate: Optional[str] = None


class SVTAV1Settings(EncoderSettings):
    name = "AV1 (SVT AV1)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    profile: str = "main"
    scene_detection: bool = False
    single_pass: bool = False
    speed: str = "7"  # Renamed preset in svtav1 encoder
    qp: Optional[Union[int, float]] = 24
    qp_mode: str = "qp"
    bitrate: Optional[str] = None
    svtav1_params: list[str] = Field(default_factory=list)


class SVTAVIFSettings(EncoderSettings):
    name = "AVIF (SVT AV1)"
    single_pass: bool = True
    speed: str = "7"  # Renamed preset in svtav1 encoder
    qp: Optional[Union[int, float]] = 24
    qp_mode: str = "qp"
    bitrate: Optional[str] = None
    svtav1_params: list[str] = Field(default_factory=list)


class VP9Settings(EncoderSettings):
    name = "VP9"
    profile: int = 2
    quality: str = "good"
    speed: str = "0"
    row_mt: int = 0
    single_pass: bool = False
    crf: Optional[Union[int, float]] = 31
    bitrate: Optional[str] = None
    fast_first_pass: Optional[bool] = True
    tile_columns: str = "-1"
    tile_rows: str = "-1"


class HEVCVideoToolboxSettings(EncoderSettings):
    name = "HEVC (Video Toolbox)"
    profile: int = 0
    allow_sw: bool = False
    require_sw: bool = False
    realtime: bool = False
    frames_before: bool = False
    frames_after: bool = False
    q: Optional[int] = 50
    bitrate: Optional[str] = None
    pix_fmt: str = "p010le"


class H264VideoToolboxSettings(EncoderSettings):
    name = "H264 (Video Toolbox)"
    profile: int = 0
    allow_sw: bool = False
    require_sw: bool = False
    realtime: bool = False
    frames_before: bool = False
    frames_after: bool = False
    q: Optional[int] = 50
    bitrate: Optional[str] = None
    pix_fmt: str = "yuv420p"


class AOMAV1Settings(EncoderSettings):
    name = "AV1 (AOM)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    usage: str = "good"
    row_mt: str = "enabled"
    cpu_used: str = "4"
    crf: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None


class WebPSettings(EncoderSettings):
    name = "WebP"
    lossless: str = "0"
    compression: str = "3"
    preset: str = "none"
    qscale: Union[int, float] = 15


class GIFSettings(EncoderSettings):
    name = "GIF"
    fps: int = 15
    dither: str = "sierra2_4a"
    max_colors: str = "256"
    stats_mode: str = "full"


class CopySettings(EncoderSettings):
    name = "Copy"


setting_types = {
    "x265": x265Settings,
    "x264": x264Settings,
    "rav1e": rav1eSettings,
    "svt_av1": SVTAV1Settings,
    "vp9": VP9Settings,
    "aom_av1": AOMAV1Settings,
    "gif": GIFSettings,
    "webp": WebPSettings,
    "copy_settings": CopySettings,
    "ffmpeg_hevc_nvenc": FFmpegNVENCSettings,
    "qsvencc_hevc": QSVEncCSettings,
    "qsvencc_av1": QSVEncCAV1Settings,
    "qsvencc_avc": QSVEncCH264Settings,
    "nvencc_hevc": NVEncCSettings,
    "nvencc_av1": NVEncCAV1Settings,
    "nvencc_avc": NVEncCAVCSettings,
    "vceencc_hevc": VCEEncCSettings,
    "vceencc_avc": VCEEncCAVCSettings,
    "hevc_videotoolbox": HEVCVideoToolboxSettings,
    "h264_videotoolbox": H264VideoToolboxSettings,
    "svt_av1_avif": SVTAVIFSettings,
}
