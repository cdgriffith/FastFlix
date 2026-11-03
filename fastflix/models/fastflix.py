# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir
from pydantic import BaseModel, Field

from fastflix.models.config import Config
from fastflix.models.video import Video

# Portable installs keep the queue, history and logs next to the portable fastflix.yaml instead of in the shared
# per-user data folder, so they don't share state with an installed FastFlix (#764)
PORTABLE_DATA_DIR = "fastflix_data"


def portable_data_path() -> Path:
    return Path(PORTABLE_DATA_DIR).absolute()


class FastFlix(BaseModel):
    audio_encoders: list[str] = None
    video_encoders: list[str] = None
    encoders: dict = None
    config: Config = None
    data_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    log_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "logs"
    queue_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "queue.yaml"
    ffmpeg_version: str = ""
    ffmpeg_config: list[str] = ""
    ffprobe_version: str = ""
    libavcodec_version: int = 0
    opencl_support: bool = False

    # Queues
    worker_queue: Any = None
    status_queue: Any = None
    log_queue: Any = None

    current_video: Video | None = None

    def use_portable_paths(self):
        self.data_path = portable_data_path()
        self.log_path = self.data_path / "logs"
        self.queue_path = self.data_path / "queue.yaml"

    # Conversion
    currently_encoding: bool = False
    conversion_paused: bool = False
    conversion_list: list[Video] = Field(default_factory=list)
    current_video_encode_index: int = 0
    current_command_encode_index: int = 0

    # State
    shutting_down: bool = False
