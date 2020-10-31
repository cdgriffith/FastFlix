# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Union, List
from pathlib import Path
from multiprocessing import Queue

from appdirs import user_data_dir

from fastflix.models.base import BaseDataClass
from fastflix.models.config import Config


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
