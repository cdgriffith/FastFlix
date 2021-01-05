# -*- coding: utf-8 -*-
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Union

from appdirs import user_data_dir
from box import Box, BoxError

from fastflix.exceptions import ConfigError, MissingFF
from fastflix.models.encode import (
    AOMAV1Settings,
    CopySettings,
    GIFSettings,
    SVTAV1Settings,
    VP9Settings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
)
from fastflix.version import __version__

fastflix_folder = Path(user_data_dir("FastFlix", appauthor=False, roaming=True))
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))

NO_OPT = object()


@dataclass
class Profile:
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

    x265: Union[x265Settings, None] = None
    x264: Union[x264Settings, None] = None
    rav1e: Union[rav1eSettings, None] = None
    svt_av1: Union[SVTAV1Settings, None] = None
    vp9: Union[VP9Settings, None] = None
    aom_av1: Union[AOMAV1Settings, None] = None
    gif: Union[GIFSettings, None] = None
    webp: Union[WebPSettings, None] = None
    copy: Union[CopySettings, None] = None

    setting_types = {
        "x265": x265Settings,
        "x264": x264Settings,
        "rav1e": rav1eSettings,
        "svt_av1": SVTAV1Settings,
        "vp9": VP9Settings,
        "aom_av1": AOMAV1Settings,
        "gif": GIFSettings,
        "webp": WebPSettings,
        "copy": CopySettings,
    }

    def to_dict(self):
        output = {}
        for k, v in asdict(self).items():
            if k in self.setting_types.keys():
                output[k] = asdict(v)
            else:
                output[k] = v


empty_profile = Profile(x265=x265Settings())


def get_preset_defaults():
    return {
        "Standard Profile": Profile(x265=x265Settings()),
        "UHD HDR10 Film": Profile(
            auto_crop=True, x265=x265Settings(crf=18, hdr10=True, hdr10_opt=True, repeat_headers=True, preset="slow")
        ),
        "1080p Film": Profile(auto_crop=True, encoder="AVC (x264)", x264=x264Settings(crf=17, preset="slow")),
    }


@dataclass
class Config:
    version: str = __version__
    config_path: Path = fastflix_folder / "fastflix.yaml"
    ffmpeg: Path = None
    ffprobe: Path = None
    flat_ui: bool = True
    language: str = "en"
    logging_level: int = 10
    continue_on_failure: bool = True
    work_path: Path = fastflix_folder
    use_sane_audio: bool = True
    selected_profile: str = "Standard Profile"
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

    def encoder_opt(self, profile_name, profile_option_name):
        encoder_settings = getattr(self.profiles[self.selected_profile], profile_name)
        if encoder_settings:
            return getattr(encoder_settings, profile_option_name)
        else:
            return getattr(empty_profile.setting_types[profile_name](), profile_option_name)

    def opt(self, profile_option_name, default=NO_OPT):
        if default != NO_OPT:
            return getattr(self.profiles[self.selected_profile], profile_option_name, default)
        return getattr(self.profiles[self.selected_profile], profile_option_name)

    def find_ffmpeg_file(self, name):
        if (ff_location := shutil.which(name)) is not None:
            return setattr(self, name, Path(ff_location).absolute())

        if not ffmpeg_folder.exists():
            raise MissingFF(name)
        for file in ffmpeg_folder.iterdir():
            if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                return setattr(self, name, file)
        else:
            if (ffmpeg_folder / "bin").exists():
                for file in (ffmpeg_folder / "bin").iterdir():
                    if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                        return setattr(self, name, file)
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
            if key == "profiles":
                self.profiles = {}
                for k, v in value.items():
                    if k in ("Standard Profile",):
                        continue
                    profile = Profile()
                    for setting_name, setting in v.items():
                        if setting_name in profile.setting_types.keys() and setting is not None:
                            setattr(profile, setting_name, profile.setting_types[setting_name](**setting))
                        else:
                            setattr(profile, setting_name, setting)

                    self.profiles[k] = profile
                continue
            if key in self and key not in ("config_path", "version"):
                setattr(self, key, Path(value) if key in paths and value else value)
        if not self.ffmpeg or not self.ffmpeg.exists():
            self.find_ffmpeg_file("ffmpeg")

        if not self.ffprobe or not self.ffprobe.exists():
            try:
                self.find_ffmpeg_file("ffprobe")
            except MissingFF as err:
                try:
                    self.find_ffmpeg_file("ffmpeg.ffprobe")
                except MissingFF:
                    raise err from None

        self.profiles.update(get_preset_defaults())

        if self.selected_profile not in self.profiles:
            self.selected_profile = "Standard Profile"

    def save(self):
        items = asdict(self)
        del items["config_path"]
        for k, v in items.items():
            if isinstance(v, Path):
                items[k] = str(v.absolute())
        items["profiles"] = {k: asdict(v) for k, v in self.profiles.items() if k not in get_preset_defaults().keys()}
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
