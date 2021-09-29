# -*- coding: utf-8 -*-
import uuid
from pathlib import Path
from typing import List, Optional, Union, Tuple

from box import Box
from pydantic import BaseModel, Field

from fastflix.models.encode import (
    AOMAV1Settings,
    AttachmentTrack,
    AudioTrack,
    CopySettings,
    GIFSettings,
    FFmpegNVENCSettings,
    SubtitleTrack,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    NVEncCSettings,
    NVEncCAVCSettings,
    VCEEncCSettings,
    VCEEncCAVCSettings,
)

__all__ = ["VideoSettings", "Status", "Video", "Crop", "Status"]


def determine_rotation(streams, track: int = 0) -> Tuple[int, int]:
    for stream in streams.video:
        if int(track) == stream["index"]:
            video_stream = stream
            break
    else:
        return 0, 0

    rotation = 0
    if "rotate" in streams.video[0].get("tags", {}):
        rotation = abs(int(video_stream.tags.rotate))

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
        FFmpegNVENCSettings,
        NVEncCSettings,
        NVEncCAVCSettings,
        VCEEncCSettings,
        VCEEncCAVCSettings,
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
    subtitle_fixed: bool = False
    current_command: int = 0

    @property
    def ready(self) -> bool:
        return not self.success and not self.error and not self.complete and not self.running and not self.cancelled

    def clear(self):
        self.success = False
        self.error = False
        self.complete = False
        self.running = False
        self.cancelled = False
        self.subtitle_fixed = False
        self.current_command = 0


class Video(BaseModel):
    source: Path
    duration: Union[float, int] = 0
    streams: Box = None

    work_path: Path = None
    format: Box = None
    interlaced: Union[str, bool] = False
    concat: bool = False

    hdr10_streams: List[Box] = Field(default_factory=list)
    hdr10_plus: List[int] = Field(default_factory=list)

    video_settings: VideoSettings = Field(default_factory=VideoSettings)
    status: Status = Field(default_factory=Status)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def width(self):
        w, _ = determine_rotation(self.streams, self.video_settings.selected_track)
        return w

    @property
    def height(self):
        _, h = determine_rotation(self.streams, self.video_settings.selected_track)
        return h

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
