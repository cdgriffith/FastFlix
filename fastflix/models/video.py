# -*- coding: utf-8 -*-
import uuid
from pathlib import Path
from typing import List, Optional, Union

from box import Box
from pydantic import BaseModel, Field

from fastflix.models.encode import (
    AOMAV1Settings,
    AttachmentTrack,
    AudioTrack,
    CopySettings,
    GIFSettings,
    SubtitleTrack,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    NVENCSettings,
)

__all__ = ["VideoSettings", "Status", "Video"]


class VideoSettings(BaseModel):
    crop: Optional[str] = None
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
    selected_track: int = 0
    output_path: Path = None
    scale: Optional[str] = None
    deinterlace: bool = False
    video_speed: Union[float, int] = 1
    tone_map: str = "hable"
    denoise: Optional[str] = None
    deblock: Optional[str] = None
    deblock_size: int = 4
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    source_fps: Optional[str] = None
    output_fps: Optional[str] = None
    vsync: Optional[str] = None
    maxrate: Optional[int] = None
    bufsize: Optional[int] = None
    video_encoder_settings: Union[
        x265Settings,
        x264Settings,
        rav1eSettings,
        SVTAV1Settings,
        AOMAV1Settings,
        VP9Settings,
        GIFSettings,
        WebPSettings,
        CopySettings,
        NVENCSettings,
    ] = None
    audio_tracks: List[AudioTrack] = Field(default_factory=list)
    subtitle_tracks: List[SubtitleTrack] = Field(default_factory=list)
    attachment_tracks: List[AttachmentTrack] = Field(default_factory=list)
    conversion_commands: List = Field(default_factory=list)


class Status(BaseModel):
    success: bool = False
    error: bool = False
    complete: bool = False
    running: bool = False
    cancelled: bool = False
    current_command: int = 0


class Video(BaseModel):
    source: Path
    width: int = 0
    height: int = 0
    duration: Union[float, int] = 0
    streams: Box = None

    work_path: Path = None
    format: Box = None
    interlaced: bool = True

    # HDR10 Details
    master_display: Box = None
    cll: str = ""
    hdr10_plus: bool = False

    video_settings: VideoSettings = Field(default_factory=VideoSettings)
    status: Status = Field(default_factory=Status)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))

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
