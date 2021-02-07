# -*- coding: utf-8 -*-
from typing import List
import os
from pathlib import Path
import logging

from box import Box, BoxError

from fastflix.models.video import Video, VideoSettings, Status, Crop
from fastflix.models.encode import AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.encode import setting_types

logger = logging.getLogger("fastflix")


def get_queue(queue_file: Path) -> List[Video]:
    if not queue_file.exists():
        return []

    try:
        loaded = Box.from_yaml(filename=queue_file)
    except BoxError:
        # TODO log
        return []

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
        crop = None
        if video["video_settings"]["crop"]:
            crop = Crop(**video["video_settings"]["crop"])
        del video["video_settings"]["audio_tracks"]
        del video["video_settings"]["subtitle_tracks"]
        del video["video_settings"]["attachment_tracks"]
        del video["video_settings"]["video_encoder_settings"]
        del video["status"]
        del video["video_settings"]["crop"]
        vs = VideoSettings(
            **video["video_settings"],
            audio_tracks=audio,
            subtitle_tracks=subtitles,
            attachment_tracks=attachments,
            crop=crop,
        )
        vs.video_encoder_settings = ves  # No idea why this has to be called after, otherwise reset to x265
        del video["video_settings"]
        queue.append(Video(**video, video_settings=vs, status=status))
    return queue


def save_queue(queue: List[Video], queue_file: Path):
    items = []
    for video in queue:
        video = video.dict()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        items.append(video)
    Box(queue=items).to_yaml(filename=queue_file)
    logger.debug(f"queue saved to recovery file {queue_file}")
