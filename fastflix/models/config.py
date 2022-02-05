#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
from distutils.version import StrictVersion
from pathlib import Path
from typing import Dict, List, Optional
import json

from appdirs import user_data_dir
from box import Box, BoxError
from pydantic import BaseModel, Field
from reusables import win_based

from fastflix.exceptions import ConfigError, MissingFF
from fastflix.models.encode import (
    x264Settings,
    x265Settings,
    setting_types,
)
from fastflix.models.profiles import Profile
from fastflix.version import __version__
from fastflix.shared import get_config

logger = logging.getLogger("fastflix")

fastflix_folder = Path(os.getenv("FF_WORKDIR", user_data_dir("FastFlix", appauthor=False, roaming=True)))
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))

NO_OPT = object()


outdated_settings = ("copy",)


def get_preset_defaults():
    return {
        "Standard Profile": Profile(x265=x265Settings()),
        "UHD HDR10 Film": Profile(
            auto_crop=True, x265=x265Settings(crf=18, hdr10=True, hdr10_opt=True, repeat_headers=True, preset="slow")
        ),
        "1080p Film": Profile(auto_crop=True, encoder="AVC (x264)", x264=x264Settings(crf=22, preset="slow")),
    }


def find_ffmpeg_file(name, raise_on_missing=False):
    if ff_location := os.getenv(f"FF_{name.upper()}"):
        return Path(ff_location).absolute()

    if not win_based and Path(name).exists() and Path(name).is_file():
        return Path(name).absolute()
    elif win_based and Path(f"{name}.exe").exists() and Path(f"{name}.exe").is_file():
        return Path(f"{name}.exe").absolute()

    if (ff_location := shutil.which(name)) is not None:
        return Path(ff_location).absolute()

    if not ffmpeg_folder.exists():
        if raise_on_missing:
            raise MissingFF(name)
        return None
    for file in ffmpeg_folder.iterdir():
        if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
            return file
    else:
        if (ffmpeg_folder / "bin").exists():
            for file in (ffmpeg_folder / "bin").iterdir():
                if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                    return file
    if raise_on_missing:
        raise MissingFF(name)
    return None


def find_hdr10plus_tool():
    if location := os.getenv("FF_HDR10PLUS"):
        return Path(location)
    if location := shutil.which("hdr10plus_tool"):
        return Path(location)
    if location := shutil.which("hdr10plus_parser"):
        return Path(location)
    return None


def where(filename: str) -> Optional[Path]:
    if location := shutil.which(filename):
        return Path(location)
    return None


class Config(BaseModel):
    version: str = __version__
    config_path: Path = Field(default_factory=get_config)
    ffmpeg: Path = Field(default_factory=lambda: find_ffmpeg_file("ffmpeg"))
    ffprobe: Path = Field(default_factory=lambda: find_ffmpeg_file("ffprobe"))
    hdr10plus_parser: Optional[Path] = Field(default_factory=find_hdr10plus_tool)
    nvencc: Optional[Path] = Field(default_factory=lambda: where("NVEncC64") or where("NVEncC"))
    vceencc: Optional[Path] = Field(default_factory=lambda: where("VCEEncC64") or where("VCEEncC"))
    output_directory: Optional[Path] = False
    source_directory: Optional[Path] = False
    output_name_format: str = "{source}-fastflix-{rand_4}.{ext}"
    flat_ui: bool = True
    language: str = "eng"
    logging_level: int = 10
    crop_detect_points: int = 10
    continue_on_failure: bool = True
    work_path: Path = fastflix_folder
    use_sane_audio: bool = True
    selected_profile: str = "Standard Profile"
    theme: str = "onyx"
    disable_version_check: bool = False
    disable_update_check: bool = False
    disable_automatic_subtitle_burn_in: bool = False
    custom_after_run_scripts: Dict = Field(default_factory=dict)
    profiles: Dict[str, Profile] = Field(default_factory=get_preset_defaults)
    sane_audio_selection: List = Field(
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

    def encoder_opt(self, profile_name, profile_option_name):
        encoder_settings = getattr(self.profiles[self.selected_profile], profile_name)
        if encoder_settings:
            return getattr(encoder_settings, profile_option_name)
        else:
            return getattr(setting_types[profile_name](), profile_option_name)

    def opt(self, profile_option_name, default=NO_OPT):
        if default != NO_OPT:
            return getattr(self.profiles[self.selected_profile], profile_option_name, default)
        return getattr(self.profiles[self.selected_profile], profile_option_name)

    def load(self):
        if not self.config_path.exists() or self.config_path.stat().st_size < 10:
            logger.debug(f"Creating new config file {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save()
            if not self.ffmpeg:
                raise MissingFF("ffmpeg")
            if not self.ffprobe:
                # Try one last time to find snap packaged versions
                self.ffprobe = find_ffmpeg_file("ffmpeg.ffprobe", raise_on_missing=True)
            return
        logger.debug(f"Using config file {self.config_path}")
        try:
            data = Box.from_yaml(filename=self.config_path)
        except BoxError as err:
            raise ConfigError(f"{self.config_path}: {err}")
        if "version" not in data:
            raise ConfigError(f"Corrupt config file. Please fix or remove {self.config_path}")

        if StrictVersion(__version__) < StrictVersion(data.version):
            logger.warning(
                f"This FastFlix version ({__version__}) is older "
                f"than the one that generated the config file ({data.version}), "
                "there may be non-recoverable errors while loading it."
            )

        paths = ("work_path", "ffmpeg", "ffprobe", "hdr10plus_parser", "nvencc", "output_directory", "source_directory")
        for key, value in data.items():
            if key == "profiles":
                self.profiles = {}
                for k, v in value.items():
                    # if k in get_preset_defaults().keys():
                    #     continue
                    # profile =
                    # for setting_name, setting in v.items():
                    #     if setting_name in outdated_settings:
                    #         continue
                    #     if setting_name in setting_types.keys() and setting is not None:
                    #         try:
                    #             setattr(profile, setting_name, setting_types[setting_name](**setting))
                    #         except (ValueError, TypeError):
                    #             logger.exception(f"Could not set profile setting {setting_name}")
                    #     if setting_name in profile_setting_types.keys() and setting is not None:
                    #         try:
                    #             setattr(profile, setting_name, profile_setting_types[setting_name](**setting))
                    #         except (ValueError, TypeError):
                    #             logger.exception(f"Could not set profile setting {setting_name}")
                    #     else:
                    #         try:
                    #             setattr(profile, setting_name, setting)
                    #         except (ValueError, TypeError):
                    #             logger.exception(f"Could not set profile setting {setting_name}")

                    self.profiles[k] = Profile(**v)
                continue
            if key in self and key not in ("config_path", "version"):
                setattr(self, key, Path(value) if key in paths and value else value)

        if not self.ffmpeg or not self.ffmpeg.exists():
            self.ffmpeg = find_ffmpeg_file("ffmpeg", raise_on_missing=True)
        if not self.ffprobe or not self.ffprobe.exists():
            try:
                self.ffprobe = find_ffmpeg_file("ffprobe", raise_on_missing=True)
            except MissingFF as err:
                try:
                    self.ffprobe = find_ffmpeg_file("ffmpeg.ffprobe", raise_on_missing=True)
                except MissingFF:
                    raise err from None
        if not self.hdr10plus_parser:
            self.hdr10plus_parser = where("hdr10plus_parser")
        if not self.nvencc:
            self.nvencc = where("NVEncC64") or where("NVEncC")
        if not self.vceencc:
            self.vceencc = where("VCEEncC64") or where("VCEEncC")
        self.profiles.update(get_preset_defaults())

        if self.selected_profile not in self.profiles:
            self.selected_profile = "Standard Profile"

    def save(self):
        items = self.dict()
        del items["config_path"]
        for k, v in items.items():
            if isinstance(v, Path):
                items[k] = str(v.absolute())
        # Need to use pydantics converters, but those only run with `.json` and not `.dict`
        items["profiles"] = {
            k: json.loads(v.json()) for k, v in self.profiles.items() if k not in get_preset_defaults().keys()
        }
        return Box(items).to_yaml(filename=self.config_path, default_flow_style=False)

    @property
    def profile(self):
        return self.profiles[self.selected_profile]

    def __iter__(self):
        return (x for x in dir(self) if not x.startswith("_"))

    def upgrade_check(self):
        old_config_path = self.config_path.parent / "fastflix.json"
        if not self.config_path.exists() and old_config_path.exists():
            data = Box.from_json(filename=old_config_path)
            if data.get("work_dir"):
                self.work_path = Path(data.work_dir)
            if data.get("ffmpeg"):
                self.ffmpeg = Path(data.ffmpeg)
            if data.get("ffprobe"):
                self.ffmpeg = Path(data.ffprobe)
            self.disable_automatic_subtitle_burn_in = data.get("disable_automatic_subtitle_burn_in")
            self.disable_update_check = data.get("disable_update_check")
            self.use_sane_audio = data.get("use_sane_audio")
            for audio_type in data.get("sane_audio_selection", []):
                if audio_type not in self.sane_audio_selection:
                    self.sane_audio_selection.append(audio_type)
            self.save()
            old_config_path.unlink(missing_ok=True)
            return True
        return False
