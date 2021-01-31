# -*- coding: utf-8 -*-
from typing import List, Optional, Union
import os
from pathlib import Path

from box import Box
from pydantic import BaseModel, Field

from fastflix.models.video import Video, VideoSettings, AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.encode import setting_types


def get_queue(queue_file):
    loaded = Box.from_yaml(filename=queue_file)
    queue = []
    for video in loaded["queue"]:
        video["source"] = Path(video["source"])
        video["work_path"] = Path(video["work_path"])
        video["video_settings"]["output_path"] = Path(video["video_settings"]["output_path"])
        encoder_settings = video["video_settings"]["video_encoder_settings"]
        ves = [x(**encoder_settings) for x in setting_types.values() if x().name == encoder_settings["name"]][0]
        audio = [AudioTrack(**x) for x in video["video_settings"]["audio_tracks"]]
        subtitles = [SubtitleTrack(**x) for x in video["video_settings"]["subtitle_tracks"]]
        attachments = [AttachmentTrack(**x) for x in video["video_settings"]["attachment_tracks"]]
        del video["video_settings"]["audio_tracks"]
        del video["video_settings"]["subtitle_tracks"]
        del video["video_settings"]["attachment_tracks"]
        del video["video_settings"]["video_encoder_settings"]
        vs = VideoSettings(
            **video["video_settings"],
            audio_tracks=audio,
            subtitle_tracks=subtitles,
            attachment_tracks=attachments,
            video_encoder_settings=ves,
        )
        del video["video_settings"]
        queue.append(Video(**video, video_settings=vs))
    return queue


def save_queue(queue: List[Video], queue_file):
    items = []
    for video in queue:
        video = video.dict()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        items.append(video)
    Box(queue=items).to_yaml(filename=queue_file)
