# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union, Tuple

from box import Box
from pydantic import BaseModel, Field, field_validator, ConfigDict

from fastflix.models.encode import (
    AOMAV1Settings,
    AttachmentTrack,
    AudioTrack,
    CopySettings,
    DataTrack,
    GIFSettings,
    GifskiSettings,
    FFmpegNVENCSettings,
    FFmpegAV1NVENCSettings,
    SubtitleTrack,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    QSVEncCSettings,
    QSVEncCH264Settings,
    QSVEncCAV1Settings,
    NVEncCSettings,
    NVEncCAVCSettings,
    NVEncCAV1Settings,
    VCEEncCSettings,
    VCEEncCAVCSettings,
    VCEEncCAV1Settings,
    HEVCVideoToolboxSettings,
    H264VideoToolboxSettings,
    SVTAVIFSettings,
    VVCSettings,
    VAAPIH264Settings,
    VAAPIHEVCSettings,
    VAAPIVP9Settings,
    VAAPIMPEG2Settings,
    ModifySettings,
)

__all__ = ["VideoSettings", "Status", "Video", "Crop", "Status"]


def get_stream_rotation(video_stream) -> int:
    """Extract rotation angle in degrees (0, 90, 180, 270) from a video stream."""
    if "rotate" in video_stream.get("tags", {}):
        return abs(int(video_stream.tags.rotate))
    for side_data in video_stream.get("side_data_list", []):
        if "rotation" in side_data:
            return abs(int(side_data.rotation))
    return 0


def determine_rotation(streams, track: int = 0) -> Tuple[int, int]:
    for stream in streams.video:
        if int(track) == stream["index"]:
            video_stream = stream
            break
    else:
        return 0, 0

    rotation = get_stream_rotation(video_stream)

    if rotation in (90, 270):
        video_width = video_stream.height
        video_height = video_stream.width
    else:
        video_width = video_stream.width
        video_height = video_stream.height
    return video_width, video_height


class Crop(BaseModel):
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0
    width: int = 0
    height: int = 0


class VideoSettings(BaseModel):
    crop: Optional[Crop] = None
    start_time: Union[float, int] = 0
    end_time: Union[float, int] = 0
    fast_seek: bool = True
    rotate: int = 0
    vertical_flip: bool = False
    horizontal_flip: bool = False
    remove_hdr: bool = False
    remove_metadata: bool = True
    copy_chapters: bool = True
    video_title: str = ""
    video_track_title: str = ""
    selected_track: int = 0
    output_path: Path | None = None
    # scale: Optional[str] = None
    resolution_method: str = "auto"
    resolution_custom: str | None = None
    deinterlace: bool = False
    deinterlace_filter: str = "yadif"
    video_speed: Union[float, int] = 1
    reverse_video: bool = False
    tone_map: str = "hable"
    denoise: Optional[str] = None
    deblock: Optional[str] = None
    deblock_size: int = 16
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    source_fps: Optional[str] = None
    output_fps: Optional[str] = None
    vsync: Optional[str] = None
    maxrate: Optional[int] = None
    bufsize: Optional[int] = None
    brightness: Optional[str] = None
    contrast: Optional[str] = None
    saturation: Optional[str] = None
    gamma: Optional[str] = None
    hue: Optional[str] = None
    sharpen: Optional[str] = None
    vibrance: Optional[str] = None
    color_temperature: Optional[str] = None
    curves_preset: Optional[str] = None
    colorbalance: Optional[str] = None
    unsharp: Optional[str] = None
    deflicker: Optional[str] = None
    pad_aspect: Optional[str] = None
    pad_color: str = "black"
    lut3d_path: Optional[str] = None
    faststart: bool = True
    gop_length: Optional[int] = None
    copy_data: bool = False
    template_generated_name: str = ""
    video_encoder_settings: Optional[
        Union[
            x265Settings,
            x264Settings,
            rav1eSettings,
            SVTAV1Settings,
            AOMAV1Settings,
            VP9Settings,
            GIFSettings,
            GifskiSettings,
            WebPSettings,
            CopySettings,
            FFmpegNVENCSettings,
            FFmpegAV1NVENCSettings,
            QSVEncCSettings,
            QSVEncCAV1Settings,
            QSVEncCH264Settings,
            NVEncCSettings,
            NVEncCAVCSettings,
            NVEncCAV1Settings,
            VCEEncCSettings,
            VCEEncCAVCSettings,
            VCEEncCAV1Settings,
            HEVCVideoToolboxSettings,
            H264VideoToolboxSettings,
            SVTAVIFSettings,
            VVCSettings,
            VAAPIH264Settings,
            VAAPIHEVCSettings,
            VAAPIVP9Settings,
            VAAPIMPEG2Settings,
            ModifySettings,
        ]
    ] = None
    # audio_tracks: list[AudioTrack] = Field(default_factory=list)
    # subtitle_tracks: list[SubtitleTrack] = Field(default_factory=list)
    # attachment_tracks: list[AttachmentTrack] = Field(default_factory=list)
    conversion_commands: List = Field(default_factory=list)

    @field_validator("brightness", mode="before")
    @classmethod
    def brightness_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("contrast", mode="before")
    @classmethod
    def contrast_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("saturation", mode="before")
    @classmethod
    def saturation_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("gamma", mode="before")
    @classmethod
    def gamma_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("hue", mode="before")
    @classmethod
    def hue_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("sharpen", mode="before")
    @classmethod
    def sharpen_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("vibrance", mode="before")
    @classmethod
    def vibrance_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

    @field_validator("color_temperature", mode="before")
    @classmethod
    def color_temperature_to_str(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value


class Status(BaseModel):
    error: bool = False
    complete: bool = False
    running: bool = False
    cancelled: bool = False
    subtitle_fixed: bool = False
    current_command: int = 0
    encode_started_at: Optional[datetime] = None

    @property
    def ready(self) -> bool:
        return not self.error and not self.complete and not self.running and not self.cancelled

    def clear(self):
        self.error = False
        self.complete = False
        self.running = False
        self.cancelled = False
        self.subtitle_fixed = False
        self.current_command = 0
        self.encode_started_at = None


class Video(BaseModel):
    source: Path
    duration: Union[float, int] = 0
    streams: Box = None

    work_path: Path | None = None
    format: Box = None
    interlaced: Union[str, bool] = False
    concat: bool = False

    hdr10_streams: list[Box] = Field(default_factory=list)
    hdr10_plus: list[int] = Field(default_factory=list)

    video_settings: VideoSettings = Field(default_factory=VideoSettings)
    audio_tracks: list[AudioTrack] = Field(default_factory=list)
    subtitle_tracks: list[SubtitleTrack] = Field(default_factory=list)
    attachment_tracks: list[AttachmentTrack] = Field(default_factory=list)
    data_tracks: list[DataTrack] = Field(default_factory=list)

    status: Status = Field(default_factory=Status)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def width(self):
        track = 0
        if hasattr(self, "video_settings"):
            track = self.video_settings.selected_track
        w, _ = determine_rotation(self.streams, track)
        return w

    @property
    def height(self):
        track = 0
        if hasattr(self, "video_settings"):
            track = self.video_settings.selected_track
        _, h = determine_rotation(self.streams, track)
        return h

    @property
    def source_rotation(self) -> int:
        """Return source rotation in degrees (0, 90, 180, 270)."""
        track = 0
        if hasattr(self, "video_settings"):
            track = self.video_settings.selected_track
        if not self.streams or not self.streams.video:
            return 0
        for stream in self.streams.video:
            if int(track) == stream["index"]:
                return get_stream_rotation(stream)
        return 0

    @property
    def master_display(self) -> Optional[Box]:
        for track in self.hdr10_streams:
            if track.index == self.video_settings.selected_track:
                return track["master_display"]
        return None

    @property
    def cll(self) -> Optional[str]:
        for track in self.hdr10_streams:
            if track.index == self.video_settings.selected_track:
                return track["cll"]
        return None

    @property
    def current_video_stream(self):
        try:
            return [x for x in self.streams.video if x.index == self.video_settings.selected_track][0]
        except IndexError:
            return None

    @property
    def color_space(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("color_space", "")

    @property
    def color_primaries(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("color_primaries", "")

    @property
    def color_transfer(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("color_transfer", "")

    @property
    def pix_fmt(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("pix_fmt", "")

    @property
    def frame_rate(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("r_frame_rate", "")

    @property
    def average_frame_rate(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("avg_frame_rate", "")

    @property
    def sar(self):
        stream = self.current_video_stream
        if not stream:
            return ""
        return stream.get("sample_aspect_ratio", "1:1")

    @staticmethod
    def compute_output_dimensions(
        source_w: int,
        source_h: int,
        crop_top: int = 0,
        crop_bottom: int = 0,
        crop_left: int = 0,
        crop_right: int = 0,
        method: str = "auto",
        custom: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[int]]:
        """Compute final output width and height after crop + scale + rounding.

        Returns (None, None) if method is "auto" or inputs are invalid.
        Returns (width, height) with the auto-calculated dimension rounded to nearest multiple of 8.
        """
        cropped_w = source_w - crop_left - crop_right
        cropped_h = source_h - crop_top - crop_bottom

        if cropped_w <= 0 or cropped_h <= 0:
            return None, None

        if method == "auto" or not custom:
            return None, None

        try:
            if method == "custom":
                parts = custom.split(":")
                if len(parts) == 2:
                    w, h = int(parts[0]), int(parts[1])
                    return (w, h) if w > 0 and h > 0 else (None, None)
                return None, None

            pixels = int(custom)
            if pixels <= 0:
                return None, None

            if method == "width":
                out_w = pixels
                out_h = ((cropped_h * pixels // cropped_w) // 8) * 8
                return out_w, max(out_h, 8)

            if method == "height":
                out_h = pixels
                out_w = ((cropped_w * pixels // cropped_h) // 8) * 8
                return max(out_w, 8), out_h

            if method == "long edge":
                if cropped_w >= cropped_h:
                    out_w = pixels
                    out_h = ((cropped_h * pixels // cropped_w) // 8) * 8
                else:
                    out_h = pixels
                    out_w = ((cropped_w * pixels // cropped_h) // 8) * 8
                return max(out_w, 8), max(out_h, 8)
        except (ValueError, ZeroDivisionError):
            return None, None

        return None, None

    @property
    def cropped_width(self) -> int:
        if not self.video_settings.crop:
            return self.width
        return self.width - self.video_settings.crop.left - self.video_settings.crop.right

    @property
    def cropped_height(self) -> int:
        if not self.video_settings.crop:
            return self.height
        return self.height - self.video_settings.crop.top - self.video_settings.crop.bottom

    @property
    def output_width(self) -> Optional[int]:
        crop = self.video_settings.crop
        w, _ = self.compute_output_dimensions(
            source_w=self.width,
            source_h=self.height,
            crop_top=crop.top if crop else 0,
            crop_bottom=crop.bottom if crop else 0,
            crop_left=crop.left if crop else 0,
            crop_right=crop.right if crop else 0,
            method=self.video_settings.resolution_method,
            custom=self.video_settings.resolution_custom,
        )
        return w

    @property
    def output_height(self) -> Optional[int]:
        crop = self.video_settings.crop
        _, h = self.compute_output_dimensions(
            source_w=self.width,
            source_h=self.height,
            crop_top=crop.top if crop else 0,
            crop_bottom=crop.bottom if crop else 0,
            crop_left=crop.left if crop else 0,
            crop_right=crop.right if crop else 0,
            method=self.video_settings.resolution_method,
            custom=self.video_settings.resolution_custom,
        )
        return h

    @property
    def scale(self) -> Optional[str]:
        ow = self.output_width
        oh = self.output_height
        if ow is None or oh is None:
            return None
        return f"{ow}:{oh}"

    model_config = ConfigDict(arbitrary_types_allowed=True)
