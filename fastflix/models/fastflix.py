# -*- coding: utf-8 -*-
from dataclasses import dataclass, field

# from multiprocessing import Queue
from pathlib import Path
from typing import Any, Dict, List, Optional

from appdirs import user_data_dir
from pydantic import BaseModel, Field

from fastflix.models.config import Config
from fastflix.models.video import Video


class FastFlix(BaseModel):
    audio_encoders: List[str] = None
    encoders: Dict = None
    config: Config = None
    data_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    log_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"
    queue_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.yaml"
    queue_lock_file: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.lock"
    ffmpeg_version: str = ""
    ffmpeg_config: List[str] = ""
    ffprobe_version: str = ""

    # Queues
    worker_queue: Any = None
    status_queue: Any = None
    log_queue: Any = None

    current_video: Optional[Video] = None
    queue: List[Video] = Field(default_factory=list)
