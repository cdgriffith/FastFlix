# -*- coding: utf-8 -*-
import uuid
from pathlib import Path
from typing import List, Union

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
)

__all__ = ["VideoSettings", "Status", "Video"]


class VideoSettings(BaseModel):
    crop: Union[str, None] = None
    start_time: Union[float, int] = 0
    end_time: Union[float, int] = 0
    fast_seek: bool = True
    rotate: Union[str, None] = None
    vertical_flip: bool = False
    horizontal_flip: bool = False
    remove_hdr: bool = False
    remove_metadata: bool = True
    copy_chapters: bool = True
    video_title: str = ""
    selected_track: int = 0
    output_path: Path = None
    scale: Union[str, None] = None
    deinterlace: bool = False
    video_speed: Union[float, int] = 1
    tone_map: str = "hable"
    denoise: Union[str, None] = None
    deblock: Union[str, None] = None
    deblock_size: int = 4
    color_space: Union[str, None] = None
    color_transfer: Union[str, None] = None
    color_primaries: Union[str, None] = None
    source_fps: Union[str, None] = None
    output_fps: Union[str, None] = None
    vsync: Union[str, None] = None
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
