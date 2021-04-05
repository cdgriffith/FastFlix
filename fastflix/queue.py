# -*- coding: utf-8 -*-
from typing import List
import os
from pathlib import Path
import logging
import shutil
import uuid

from box import Box, BoxError
from ruamel.yaml import YAMLError

from fastflix.models.video import Video, VideoSettings, Status, Crop
from fastflix.models.encode import AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.encode import setting_types
from fastflix.models.config import Config

logger = logging.getLogger("fastflix")


def get_queue(queue_file: Path, config: Config) -> List[Video]:
    if not queue_file.exists():
        return []

    try:
        loaded = Box.from_yaml(filename=queue_file)
    except (BoxError, YAMLError):
        logger.exception("Could not open queue")
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
        attachments = []
        for x in video["video_settings"]["attachment_tracks"]:
            try:
                attachment_path = x.pop("file_path")
            except KeyError:
                attachment_path = None
            attachment = AttachmentTrack(**x)
            attachment.file_path = Path(attachment_path)
            attachments.append(attachment)
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


def save_queue(queue: List[Video], queue_file: Path, config: Config):
    items = []
    queue_covers = config.work_path / "covers"
    queue_covers.mkdir(parents=True, exist_ok=True)
    queue_data = config.work_path / "queue_extras"
    queue_data.mkdir(parents=True, exist_ok=True)

    def update_conversion_command(vid, old_path: str, new_path: str):
        for command in vid["video_settings"]["conversion_commands"]:
            new_command = command["command"].replace(old_path, new_path)
            if new_command == command["command"]:
                logger.error(f'Could not replace "{old_path}" with "{new_path}" in {command["command"]}')
            command["command"] = new_command

    for video in queue:
        video = video.dict()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        if metadata := video["video_settings"]["video_encoder_settings"].get("hdr10plus_metadata"):
            new_metadata_file = queue_data / f"{uuid.uuid4().hex}_metadata.json"
            try:
                shutil.copy(metadata, new_metadata_file)
            except OSError:
                logger.exception("Could not save HDR10+ metadata file to queue recovery location, removing HDR10+")

            update_conversion_command(
                video,
                str(metadata),
                str(new_metadata_file),
            )
            video["video_settings"]["video_encoder_settings"]["hdr10plus_metadata"] = str(new_metadata_file)
        for track in video["video_settings"]["attachment_tracks"]:
            if track.get("file_path"):
                new_file = queue_covers / f'{uuid.uuid4().hex}_{track["file_path"].name}'
                try:
                    shutil.copy(track["file_path"], new_file)
                except OSError:
                    logger.exception("Could not save cover to queue recovery location, removing cover")
                update_conversion_command(video, str(track["file_path"]), str(new_file))
                track["file_path"] = str(new_file)

        items.append(video)
    Box(queue=items).to_yaml(filename=queue_file)
    logger.debug(f"queue saved to recovery file {queue_file}")
