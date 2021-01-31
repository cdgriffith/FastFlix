# -*- coding: utf-8 -*-
from typing import List, Optional, Union
import os
from pathlib import Path

from box import Box
from pydantic import BaseModel, Field
from filelock import FileLock
from appdirs import user_data_dir

from fastflix.models.video import Video, VideoSettings, Status, Crop
from fastflix.models.encode import AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.encode import setting_types

queue_file = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.yaml"
lock_file = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.lock"


def get_queue() -> List[Video]:
    with FileLock(lock_file):
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
        status = Status(**video["status"])
        crop = Crop(**video["crop"])
        del video["video_settings"]["audio_tracks"]
        del video["video_settings"]["subtitle_tracks"]
        del video["video_settings"]["attachment_tracks"]
        del video["video_settings"]["video_encoder_settings"]
        del video["status"]
        del video["crop"]
        vs = VideoSettings(
            **video["video_settings"],
            audio_tracks=audio,
            subtitle_tracks=subtitles,
            attachment_tracks=attachments,
            video_encoder_settings=ves,
            crop=crop,
        )
        del video["video_settings"]
        queue.append(Video(**video, video_settings=vs, status=status))
    return queue


def save_queue(queue: List[Video]):
    items = []
    for video in queue:
        video = video.dict()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        items.append(video)
    with FileLock(lock_file):
        Box(queue=items).to_yaml(filename=queue_file)
