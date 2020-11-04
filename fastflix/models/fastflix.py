# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from multiprocessing import Queue
from pathlib import Path
from typing import List, Union

from appdirs import user_data_dir

from fastflix.models.base import BaseDataClass
from fastflix.models.config import Config
from fastflix.models.video import Video


@dataclass
class FastFlix(BaseDataClass):
    audio_encoders: List[str] = None
    encoders: List = None
    config: Config = None
    data_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    log_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"
    ffmpeg_version: str = ""
    ffmpeg_config: List[str] = ""
    worker_queue: Queue = None
    status_queue: Queue = None
    log_queue: Queue = None
    current_video: Union[Video, None] = None
    queue: List[Video] = field(default_factory=list)
