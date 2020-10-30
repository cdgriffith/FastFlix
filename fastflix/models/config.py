# -*- coding: utf-8 -*-
from pathlib import Path
from dataclasses import dataclass, asdict, field
import shutil
from typing import List, Dict

from appdirs import user_data_dir
from box import Box

from fastflix.version import __version__

fastflix_folder = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))


class MissingFF(Exception):
    """Required files not found"""


@dataclass
class Config:
    version: str = __version__
    config_path: Path = fastflix_folder / "fastflix.yaml"
    ffmpeg: Path = None
    ffprobe: Path = None
    language: str = "en"
    work_path: Path = fastflix_folder
    use_sane_audio: bool = True
    disable_version_check: bool = False
    disable_update_check: bool = False
    disable_automatic_subtitle_burn_in: bool = False
    custom_after_run_scripts: Dict = field(default_factory=dict)
    sane_audio_selection: List = (
        "aac",
        "ac3",
        "alac",
        "dca",
        "dts",
        "eac3",
        "flac",
        "libfdk_aac",
        "libmp3lame",
        "libopus",
        "libvorbis",
        "libwavpack",
        "mlp",
        "opus",
        "snoicls",
        "sonic",
        "truehd",
        "tta",
        "vorbis",
        "wavpack",
    )

    def find_ffmpeg_file(self, name):
        if ff_location := shutil.which(name):
            return setattr(self, name, Path(ff_location).resolve())

        if not ffmpeg_folder.exists():
            raise MissingFF(f"Could not find {name}")
        for file in ffmpeg_folder.iterdir():
            if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                setattr(self, name, file)
                break
        else:
            if (ffmpeg_folder / "bin").exists():
                for file in (ffmpeg_folder / "bin").iterdir():
                    if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                        setattr(self, name, file)
                        break
                else:
                    raise MissingFF(name)
        raise MissingFF(name)

    def load(self):
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.find_ffmpeg_file("ffmpeg")
                self.find_ffmpeg_file("ffprobe")
            finally:
                self.save()
            return

        data = Box.from_yaml(filename=self.config_path)
        paths = ("work_dir", "ffmpeg", "ffprobe")
        for key, value in data.items():
            if key in self and key not in ("config_path", "version"):
                setattr(self, key, Path(value) if key in paths else value)
        if not self.ffmpeg or not self.ffmpeg.exists():
            self.find_ffmpeg_file("ffmpeg")

        if not self.ffprobe or not self.ffprobe.exists():
            self.find_ffmpeg_file("ffprobe")

    def save(self):
        items = asdict(self)
        del items["config_path"]
        for k, v in items.items():
            if isinstance(v, Path):
                items[k] = str(v.absolute())
        return Box().to_yaml(filename=self.config_path, default_flow_style=True)

    def __iter__(self):
        return (x for x in dir(self) if not x.startswith("_"))
