# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from box import Box
from pydantic import BaseModel, Field


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


class QueueItem(BaseModel):
    video_uuid: str
    command_uuid: str
    command: str
    work_dir: str
    filename: str
    status: Union[STATUS.CONVERTED, STATUS.CANCELLED, STATUS.IN_PROGRESS, STATUS.ERRORED, STATUS.READY]


class Queue(BaseModel):
    revision: int = 0
    request: Optional[
        Union[REQUEST.CANCEL, REQUEST.PAUSE_QUEUE, REQUEST.RESUME_QUEUE, REQUEST.PAUSE_ENCODE, REQUEST.RESUME_ENCODE]
    ] = None
    queue: List[QueueItem] = Field(default_factory=list)
    after_done_command: Optional[str] = None


def get_queue(queue_file):
    loaded = Box.from_yaml(filename=queue_file)
    queue = Queue(revision=loaded.revision, request=loaded.request, after_done_command=loaded.after_done_command)
    queue.request = [QueueItem(**item) for item in loaded.queue]
    return queue


def save_queue(queue, queue_file):
    queue.revision += 1
    Box(queue.dict()).to_yaml(filename=queue_file)
