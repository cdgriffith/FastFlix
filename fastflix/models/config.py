# -*- coding: utf-8 -*-
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Union

from appdirs import user_data_dir
from box import Box, BoxError

from fastflix.version import __version__

fastflix_folder = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))

NO_OPT = object()


class MissingFF(Exception):
    """Required files not found"""


class ConfigError(Exception):
    pass


@dataclass
class Profile:
    auto_crop: bool = False
    keep_aspect_ratio: bool = True
    fast_seek: bool = True
    rotate: int = 0
    flip: int = 0
    copy_chapters: bool = True
    remove_metadata: bool = True
    remove_hdr: bool = False
    max_muxing_queue_size: str = "1024"
    custom_ffmpeg: str = ""
    encoder: str = "HEVC (x265)"
    subtitle_language: str = "en"
    subtitle_automatic_burn_in: bool = True
    subtitle_only_preferred_language: bool = True
    x265_mode: str = "crf"
    x265_crf: int = 28
    x265_bitrate: str = "28000k"
    x265_preset: str = "medium"
    x265_tune: str = "default"
    x265_profile: str = "default"
    x265_hdr10_signaling: bool = True
    x265_hdr10_opt: bool = True
    x265_dhdr10_opt: bool = False
    x265_repeat_headers: bool = True
    x265_aq: int = 2
    x265_params: str = ""
    x265_intra_encoding: bool = False


def get_preset_defaults():
    return {
        "standard": Profile(),
        "film": Profile(auto_crop=True, x265_crf=20, x265_mode="crf", x265_preset="slow"),
        "test": Profile(
            keep_aspect_ratio=False,
            auto_crop=True,
            rotate=180,
            flip=2,
            copy_chapters=False,
            remove_metadata=True,
            remove_hdr=True,
        ),
    }


@dataclass
class Config:
    version: str = __version__
    config_path: Path = fastflix_folder / "fastflix.yaml"
    ffmpeg: Path = None
    ffprobe: Path = None
    language: str = "en"
    work_path: Path = fastflix_folder
    use_sane_audio: bool = True
    default_profile: str = "standard"
    disable_version_check: bool = False
    disable_update_check: bool = False
    disable_automatic_subtitle_burn_in: bool = False
    custom_after_run_scripts: Dict = field(default_factory=dict)
    profiles: Dict[str, Profile] = field(default_factory=get_preset_defaults)
    sane_audio_selection: List = field(
        default_factory=lambda: [
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
            "snoicls",
            "sonic",
            "truehd",
            "tta",
        ]
    )

    def opt(self, profile_option_name, default=NO_OPT):
        if default != NO_OPT:
            return getattr(self.profiles[self.default_profile], profile_option_name, default)
        return getattr(self.profiles[self.default_profile], profile_option_name)

    def find_ffmpeg_file(self, name):
        if ff_location := shutil.which(name):
            return setattr(self, name, Path(ff_location).resolve())

        if not ffmpeg_folder.exists():
            raise MissingFF(name)
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

    def load(self):
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.find_ffmpeg_file("ffmpeg")
                self.find_ffmpeg_file("ffprobe")
            finally:
                self.save()
            return
        try:
            data = Box.from_yaml(filename=self.config_path)
        except BoxError as err:
            raise ConfigError(f"{self.config_path}: {err}")
        paths = ("work_path", "ffmpeg", "ffprobe")
        for key, value in data.items():
            if key == "defaults":
                self.profiles = {k: Profile(**v) for k, v in value.items() if k != "standard"}
                continue
            if key in self and key not in ("config_path", "version"):
                setattr(self, key, Path(value) if key in paths and value else value)
        if not self.ffmpeg or not self.ffmpeg.exists():
            self.find_ffmpeg_file("ffmpeg")

        if not self.ffprobe or not self.ffprobe.exists():
            self.find_ffmpeg_file("ffprobe")

        self.profiles = get_preset_defaults()

    def save(self):
        items = asdict(self)
        del items["config_path"]
        for k, v in items.items():
            if isinstance(v, Path):
                items[k] = str(v.absolute())
        items["profiles"] = {k: asdict(v) for k, v in self.profiles.items() if k not in get_preset_defaults().keys()}
        return Box(items).to_yaml(filename=self.config_path, default_flow_style=False)

    def __iter__(self):
        return (x for x in dir(self) if not x.startswith("_"))

    # def upgrade_check(self):
    #     old_config_path = self.config_path.parent / "fastflix.json"
    #     if not self.config_path.exists() and old_config_path.exists():
    #         data = Box.from_yaml(filename=self.config_path)
