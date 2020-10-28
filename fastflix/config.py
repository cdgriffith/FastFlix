# -*- coding: utf-8 -*-
from pathlib import Path
from dataclasses import dataclass, field

from appdirs import user_data_dir


@dataclass
class Config:
    config_path: Path = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
    _ffmpeg: str = field(init=True, repr=False)
    _ffprobe: str = field(init=True, repr=False)

    @property
    def ffmpeg(self):
        return self._ffmpeg

    @ffmpeg.setter
    def set_ffmpeg(self, ffmpeg):
        self._ffmpeg = ffmpeg


if __name__ == "__main__":
    config = Config()
    config.ffmpeg = "test"
    print(config.ffmpeg)
