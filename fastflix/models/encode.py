#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator
from box import Box


class AudioTrack(BaseModel):
    index: int
    outdex: int
    codec: str = ""
    downmix: Optional[str] = None
    title: str = ""
    language: str = ""
    conversion_aq: Optional[int] = None
    conversion_bitrate: Optional[str] = None
    conversion_codec: str = ""
    profile: Optional[str] = None
    enabled: bool = True
    original: bool = False
    channels: int = 2
    friendly_info: str = ""
    raw_info: Optional[Union[dict, Box]] = None
    dispositions: dict = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class SubtitleTrack(BaseModel):
    index: int
    outdex: int
    disposition: Optional[str] = ""
    burn_in: bool = False
    language: str = ""
    subtitle_type: str = ""
    dispositions: dict = Field(default_factory=dict)
    enabled: bool = True
    long_name: str = ""
    raw_info: Optional[Union[dict, Box]] = None

    class Config:
        arbitrary_types_allowed = True


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
    name: str = "HEVC (x265)"  # MUST match encoder main.name
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
    # gop_size: int = 0
    bitrate_passes: int = 2


class VVCSettings(EncoderSettings):
    name: str = "VVC"  # MUST match encoder main.name
    preset: str = "medium"
    qp: Optional[Union[int, float]] = 22
    bitrate: Optional[str] = None
    vvc_params: list[str] = Field(default_factory=list)
    tier: str = "main"
    subjopt: bool = True
    levelidc: str | None = None
    period: int | None = None


class x264Settings(EncoderSettings):
    name: str = "AVC (x264)"
    preset: str = "medium"
    profile: str = "default"
    tune: Optional[str] = None
    pix_fmt: str = "yuv420p"
    crf: Optional[Union[int, float]] = 23
    bitrate: Optional[str] = None
    bitrate_passes: int = 2


class FFmpegNVENCSettings(EncoderSettings):
    name: str = "HEVC (NVENC)"
    preset: str = "slow"
    profile: str = "main"
    tune: str = "hq"
    pix_fmt: str = "p010le"
    bitrate: Optional[str] = "6000k"
    qp: Optional[Union[int, float]] = None
    cq: int = 0
    spatial_aq: int = 0
    rc_lookahead: int = 0
    rc: Optional[str] = None
    tier: str = "main"
    level: Optional[str] = None
    gpu: int = -1
    b_ref_mode: str = "disabled"
    hw_accel: bool = False

    @field_validator("qp", mode="before")
    @classmethod
    def qp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class NVEncCSettings(EncoderSettings):
    name: str = "HEVC (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    device: int = 0
    decoder: str = "Auto"
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class NVEncCAV1Settings(EncoderSettings):
    name: str = "AV1 (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    device: int = 0
    decoder: str = "Auto"
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class QSVEncCSettings(EncoderSettings):
    name: str = "HEVC (QSVEncC)"
    preset: str = "best"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    qp_mode: str = "cqp"
    decoder: str = "Auto"
    adapt_ref: bool = False
    adapt_cqm: bool = False
    adapt_ltr: bool = False
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class QSVEncCAV1Settings(EncoderSettings):
    name: str = "AV1 (QSVEncC)"
    preset: str = "best"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    qp_mode: str = "cqp"
    decoder: str = "Auto"
    adapt_ref: bool = False
    adapt_cqm: bool = False
    adapt_ltr: bool = False
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class QSVEncCH264Settings(EncoderSettings):
    name: str = "AVC (QSVEncC)"
    preset: str = "best"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    qp_mode: str = "cqp"
    decoder: str = "Auto"
    adapt_ref: bool = False
    adapt_cqm: bool = False
    adapt_ltr: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class NVEncCAVCSettings(EncoderSettings):
    name: str = "AVC (NVEncC)"
    preset: str = "quality"
    profile: str = "auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    device: int = 0
    decoder: str = "Auto"

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class VCEEncCSettings(EncoderSettings):
    name: str = "HEVC (VCEEncC)"
    preset: str = "slow"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    decoder: str = "Auto"
    device: int = 0
    pa_sc: str = "medium"
    pa_ss: str = "high"
    pa_activity_type: str = "y"
    pa_caq_strength: str = "medium"
    pa_initqpsc: int | None = None
    pa_lookahead: int | None = None
    pa_fskip_maxqp: int = 35
    pa_ltr: bool = True
    pa_paq: str | None = None
    pa_taq: int | None = None
    pa_motion_quality: str | None = None
    output_depth: str | None = None
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class VCEEncCAV1Settings(EncoderSettings):
    name: str = "AV1 (VCEEncC)"
    preset: str = "slower"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    decoder: str = "Auto"
    bitrate_mode: str = "vbr"
    device: int = 0
    pa_sc: str = "medium"
    pa_ss: str = "high"
    pa_activity_type: str = "y"
    pa_caq_strength: str = "medium"
    pa_initqpsc: int | None = None
    pa_lookahead: int | None = None
    pa_fskip_maxqp: int = 35
    pa_ltr: bool = True
    pa_paq: str | None = None
    pa_taq: int | None = None
    pa_motion_quality: str | None = None
    output_depth: str | None = None
    copy_hdr10: bool = False

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class VCEEncCAVCSettings(EncoderSettings):
    name: str = "AVC (VCEEncC)"
    preset: str = "slow"
    profile: str = "Auto"
    bitrate: Optional[str] = "5000k"
    cqp: Optional[Union[int, float]] = None
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
    decoder: str = "Auto"
    device: int = 0
    pa_sc: str = "medium"
    pa_ss: str = "high"
    pa_activity_type: str = "y"
    pa_caq_strength: str = "medium"
    pa_initqpsc: int | None = None
    pa_lookahead: int | None = None
    pa_fskip_maxqp: int = 35
    pa_ltr: bool = True
    pa_paq: str | None = None
    pa_taq: int | None = None
    pa_motion_quality: str | None = None
    output_depth: str | None = None

    @field_validator("cqp", mode="before")
    @classmethod
    def cqp_to_int(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class rav1eSettings(EncoderSettings):
    name: str = "AV1 (rav1e)"
    speed: str = "-1"
    tile_columns: str = "-1"
    tile_rows: str = "-1"
    tiles: str = "0"
    single_pass: bool = False
    qp: Optional[Union[int, float]] = 24
    bitrate: Optional[str] = None


class SVTAV1Settings(EncoderSettings):
    name: str = "AV1 (SVT AV1)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    scene_detection: bool = False
    single_pass: bool = False
    speed: str = "7"  # Renamed preset in svtav1 encoder
    qp: Optional[Union[int, float]] = 24
    qp_mode: str = "qp"
    bitrate: Optional[str] = None
    svtav1_params: list[str] = Field(default_factory=list)


class SVTAVIFSettings(EncoderSettings):
    name: str = "AVIF (SVT AV1)"
    single_pass: bool = True
    speed: str = "7"  # Renamed preset in svtav1 encoder
    qp: Optional[Union[int, float]] = 24
    qp_mode: str = "qp"
    bitrate: Optional[str] = None
    svtav1_params: list[str] = Field(default_factory=list)


class VP9Settings(EncoderSettings):
    name: str = "VP9"
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
    name: str = "HEVC (Video Toolbox)"
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
    name: str = "H264 (Video Toolbox)"
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
    name: str = "AV1 (AOM)"
    tile_columns: str = "0"
    tile_rows: str = "0"
    usage: str = "good"
    row_mt: str = "enabled"
    cpu_used: str = "4"
    crf: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None


class WebPSettings(EncoderSettings):
    name: str = "WebP"
    lossless: str = "no"
    compression: str = "3"
    preset: str = "none"
    qscale: Union[int, float] = 75

    @field_validator("lossless", mode="before")
    @classmethod
    def losslessq_new_value(cls, value):
        if value == "0":
            return "no"
        if value == "1":
            return "yes"
        return value

    @field_validator("qscale", mode="before")
    @classmethod
    def qscale_new_value(cls, value):
        if isinstance(value, str):
            return int(value)
        return value


class GIFSettings(EncoderSettings):
    name: str = "GIF"
    fps: str = "15"
    dither: str = "sierra2_4a"
    max_colors: str = "256"
    stats_mode: str = "full"

    @field_validator("fps", mode="before")
    @classmethod
    def fps_field_validate(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        if not value.isdigit():
            raise ValueError("FPS must be a while number")
        return value


class CopySettings(EncoderSettings):
    name: str = "Copy"


class VAAPIH264Settings(EncoderSettings):
    name: str = "VAAPI H264"  # must be same as encoder name in main

    vaapi_device: str = "/dev/dri/renderD128"
    low_power: bool = False
    idr_interval: str = "0"
    b_depth: str = "1"
    async_depth: str = "2"
    aud: bool = False
    level: Optional[str] = "auto"
    rc_mode: str = "auto"
    qp: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None
    pix_fmt: str = "vaapi"


class VAAPIHEVCSettings(EncoderSettings):
    name: str = "VAAPI HEVC"

    vaapi_device: str = "/dev/dri/renderD128"
    low_power: bool = False
    idr_interval: str = "0"
    b_depth: str = "1"
    async_depth: str = "2"
    aud: bool = False
    level: Optional[str] = "auto"
    rc_mode: str = "auto"
    qp: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None
    pix_fmt: str = "vaapi"


class VAAPIVP9Settings(EncoderSettings):
    name: str = "VAAPI VP9"

    vaapi_device: str = "/dev/dri/renderD128"
    low_power: bool = False
    idr_interval: str = "0"
    b_depth: str = "1"
    rc_mode: str = "auto"
    qp: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None
    pix_fmt: str = "vaapi"


class VAAPIMPEG2Settings(EncoderSettings):
    name: str = "VAAPI MPEG2"

    vaapi_device: str = "/dev/dri/renderD128"
    low_power: bool = False
    idr_interval: str = "0"
    b_depth: str = "1"
    rc_mode: str = "auto"
    qp: Optional[Union[int, float]] = 26
    bitrate: Optional[str] = None
    pix_fmt: str = "vaapi"


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
    "vceencc_av1": VCEEncCAV1Settings,
    "vceencc_avc": VCEEncCAVCSettings,
    "hevc_videotoolbox": HEVCVideoToolboxSettings,
    "h264_videotoolbox": H264VideoToolboxSettings,
    "svt_av1_avif": SVTAVIFSettings,
    "vvc": VVCSettings,
    "vaapi_h264": VAAPIH264Settings,
    "vaapi_hevc": VAAPIHEVCSettings,
    "vaapi_vp9": VAAPIVP9Settings,
    "vaapi_mpeg2": VAAPIMPEG2Settings,
}
