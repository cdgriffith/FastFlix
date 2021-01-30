# -*- coding: utf-8 -*-
from typing import List, Optional, Union
import os
from pathlib import Path

from box import Box
from pydantic import BaseModel, Field

from fastflix.models.video import Video


class STATUS:
    CONVERTED = "converted"
    CANCELLED = "cancelled"
    ERRORED = "errored"
    IN_PROGRESS = "in_progress"
    READY = "ready"


class REQUEST:
    CANCEL = "cancel"
    PAUSE_ENCODE = "pause_encode"
    RESUME_ENCODE = "resume_encode"
    PAUSE_QUEUE = "pause_queue"
    RESUME_QUEUE = "resume_queue"


# class QueueItem(BaseModel):
#     video_uuid: str
#     command_uuid: str
#     command: str
#     work_dir: str
#     filename: str
#     status: Union[STATUS.CONVERTED, STATUS.CANCELLED, STATUS.IN_PROGRESS, STATUS.ERRORED, STATUS.READY]


class Queue(BaseModel):
    # request: Optional[
    #     Union[REQUEST.CANCEL, REQUEST.PAUSE_QUEUE, REQUEST.RESUME_QUEUE, REQUEST.PAUSE_ENCODE, REQUEST.RESUME_ENCODE]
    # ] = None
    queue: List[Video] = Field(default_factory=list)
    after_done_command: Optional[str] = None


def get_queue(queue_file):
    loaded = Box.from_yaml(filename=queue_file)
    for video in loaded["video"]:
        video["source"] = Path(video["source"])
        video["work_path"] = Path(video["work_path"])
        video["video_settings"]["output_path"] = Path(video["video_settings"]["output_path"])

    queue = Queue(after_done_command=loaded.after_done_command)
    queue.queue = [Video(**video) for video in loaded["video"]]

    # queue.request = [QueueItem(**item) for item in loaded.queue]
    return queue


def save_queue(queue, queue_file):
    queue.revision += 1
    dict_queue = queue.dict()
    for video in dict_queue["video"]:
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])

    Box().to_yaml(filename=queue_file)
