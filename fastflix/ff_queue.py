# -*- coding: utf-8 -*-
from typing import Optional
import os
from pathlib import Path
import logging
import shutil
import uuid
import gc

from box import Box, BoxError
from ruamel.yaml import YAMLError

from fastflix.models.video import Video, VideoSettings, Status, Crop
from fastflix.models.encode import AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.encode import setting_types
from fastflix.models.config import Config

logger = logging.getLogger("fastflix")


def get_queue(queue_file: Path) -> list[Video]:
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
        # audio = [AudioTrack(**x) for x in video["audio_tracks"]]
        # subtitles = [SubtitleTrack(**x) for x in video["subtitle_tracks"]]
        attachments = []
        for x in video["attachment_tracks"]:
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
        del video["video_settings"]["video_encoder_settings"]
        del video["status"]
        del video["video_settings"]["crop"]
        vs = VideoSettings(
            **video["video_settings"],
            crop=crop,
        )
        vs.video_encoder_settings = ves  # No idea why this has to be called after, otherwise reset to x265
        del video["video_settings"]
        queue.append(Video(**video, video_settings=vs, status=status))
    del loaded
    return queue


def save_queue(queue: list[Video], queue_file: Path, config: Optional[Config] = None):
    items = []

    if config is not None:
        queue_covers = config.work_path / "covers"
        queue_covers.mkdir(parents=True, exist_ok=True)
        queue_data = config.work_path / "queue_extras"
        queue_data.mkdir(parents=True, exist_ok=True)
    else:
        queue_data = Path()
        queue_covers = Path()

    def update_conversion_command(vid, old_path: str, new_path: str):
        for command in vid["video_settings"]["conversion_commands"]:
            new_command = command["command"].replace(old_path, new_path)
            if new_command == command["command"]:
                logger.error(f'Could not replace "{old_path}" with "{new_path}" in {command["command"]}')
            command["command"] = new_command

    for video in queue:
        video = video.model_dump()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        if config:
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
            for track in video["attachment_tracks"]:
                if track.get("file_path"):
                    if not Path(track["file_path"]).exists():
                        logger.exception("Could not save cover to queue recovery location, removing cover")
                        continue
                    new_file = queue_covers / f'{uuid.uuid4().hex}_{track["file_path"].name}'
                    try:
                        shutil.copy(track["file_path"], new_file)
                    except OSError:
                        logger.exception("Could not save cover to queue recovery location, removing cover")
                        continue
                    update_conversion_command(video, str(track["file_path"]), str(new_file))
                    track["file_path"] = str(new_file)

        items.append(video)
    try:
        tmp = Box(queue=items)
        tmp.to_yaml(filename=queue_file)
        del tmp
    except Exception as err:
        logger.warning(items)
        logger.exception(f"Could not save queue! {err.__class__.__name__}: {err}")
        raise err from None
    gc.collect(2)
