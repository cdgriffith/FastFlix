#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil
from distutils.version import StrictVersion
from pathlib import Path
from typing import Dict, List, Optional

from appdirs import user_data_dir
from box import Box, BoxError
from pydantic import BaseModel, Field

from fastflix.exceptions import ConfigError, MissingFF
from fastflix.models.encode import (
    AOMAV1Settings,
    CopySettings,
    GIFSettings,
    FFmpegNVENCSettings,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
    NVEncCSettings,
    NVEncCAVCSettings,
    setting_types,
)
from fastflix.version import __version__

logger = logging.getLogger("fastflix")

fastflix_folder = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))

NO_OPT = object()


outdated_settings = ("copy",)


class Profile(BaseModel):
    auto_crop: bool = False
    keep_aspect_ratio: bool = True
    fast_seek: bool = True
    rotate: int = 0
    vertical_flip: bool = False
    horizontal_flip: bool = False
    copy_chapters: bool = True
    remove_metadata: bool = True
    remove_hdr: bool = False
    encoder: str = "HEVC (x265)"

    audio_language: str = "en"
    audio_select: bool = True
    audio_select_preferred_language: bool = True
    audio_select_first_matching: bool = False

    subtitle_language: str = "en"
    subtitle_select: bool = True
    subtitle_select_preferred_language: bool = True
    subtitle_automatic_burn_in: bool = False
    subtitle_select_first_matching: bool = False

    x265: Optional[x265Settings] = None
    x264: Optional[x264Settings] = None
    rav1e: Optional[rav1eSettings] = None
    svt_av1: Optional[SVTAV1Settings] = None
    vp9: Optional[VP9Settings] = None
    aom_av1: Optional[AOMAV1Settings] = None
    gif: Optional[GIFSettings] = None
    webp: Optional[WebPSettings] = None
    copy_settings: Optional[CopySettings] = None
    ffmpeg_hevc_nvenc: Optional[FFmpegNVENCSettings] = None
    nvencc_hevc: Optional[NVEncCSettings] = None
    nvencc_avc: Optional[NVEncCAVCSettings] = None


empty_profile = Profile(x265=x265Settings())


def get_preset_defaults():
    return {
        "Standard Profile": Profile(x265=x265Settings()),
        "UHD HDR10 Film": Profile(
            auto_crop=True, x265=x265Settings(crf=18, hdr10=True, hdr10_opt=True, repeat_headers=True, preset="slow")
        ),
        "1080p Film": Profile(auto_crop=True, encoder="AVC (x264)", x264=x264Settings(crf=22, preset="slow")),
    }


def find_ffmpeg_file(name, raise_on_missing=False):
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


def where(filename: str) -> Optional[Path]:
    if location := shutil.which(filename):
        return Path(location)
    return None


class Config(BaseModel):
    version: str = __version__
    config_path: Path = fastflix_folder / "fastflix.yaml"
    ffmpeg: Path = Field(default_factory=lambda: find_ffmpeg_file("ffmpeg"))
    ffprobe: Path = Field(default_factory=lambda: find_ffmpeg_file("ffprobe"))
    hdr10plus_parser: Optional[Path] = Field(default_factory=lambda: where("hdr10plus_parser"))
    mkvpropedit: Optional[Path] = Field(default_factory=lambda: where("mkvpropedit"))
    nvencc: Optional[Path] = Field(default_factory=lambda: where("NVEncC"))
    output_directory: Optional[Path] = False
    flat_ui: bool = True
    language: str = "en"
    logging_level: int = 10
    crop_detect_points: int = 10
    continue_on_failure: bool = True
    work_path: Path = fastflix_folder
    use_sane_audio: bool = True
    selected_profile: str = "Standard Profile"
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
        if not self.config_path.exists():
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
        if StrictVersion(__version__) < StrictVersion(data.version):
            logger.warning(
                f"This FastFlix version ({__version__}) is older "
                f"than the one that generated the config file ({data.version}), "
                "there may be non-recoverable errors while loading it."
            )

        paths = ("work_path", "ffmpeg", "ffprobe", "hdr10plus_parser", "mkvpropedit", "nvencc", "output_directory")
        for key, value in data.items():
            if key == "profiles":
                self.profiles = {}
                for k, v in value.items():
                    if k in get_preset_defaults().keys():
                        continue
                    profile = Profile()
                    for setting_name, setting in v.items():
                        if setting_name in outdated_settings:
                            continue
                        if setting_name in setting_types.keys() and setting is not None:
                            try:
                                setattr(profile, setting_name, setting_types[setting_name](**setting))
                            except (ValueError, TypeError):
                                logger.exception(f"Could not set profile setting {setting_name}")
                        else:
                            try:
                                setattr(profile, setting_name, setting)
                            except (ValueError, TypeError):
                                logger.exception(f"Could not set profile setting {setting_name}")

                    self.profiles[k] = profile
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
        if not self.mkvpropedit:
            self.mkvpropedit = where("mkvpropedit")
        if not self.nvencc:
            self.mkvpropedit = where("NVEncC")
        self.profiles.update(get_preset_defaults())

        if self.selected_profile not in self.profiles:
            self.selected_profile = "Standard Profile"

    def save(self):
        items = self.dict()
        del items["config_path"]
        for k, v in items.items():
            if isinstance(v, Path):
                items[k] = str(v.absolute())
        items["profiles"] = {k: v.dict() for k, v in self.profiles.items() if k not in get_preset_defaults().keys()}
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
