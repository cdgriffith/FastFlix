#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
from packaging import version
from pathlib import Path
from typing import Literal
import json

from platformdirs import user_data_dir
from box import Box, BoxError
from pydantic import BaseModel, Field
from reusables import win_based

from fastflix.exceptions import ConfigError, MissingFF
from fastflix.models.encode import (
    x264Settings,
    x265Settings,
    setting_types,
)
from fastflix.models.profiles import Profile, AudioMatch, MatchItem, MatchType
from fastflix.version import __version__
from fastflix.rigaya_helpers import get_all_encoder_formats_and_devices

logger = logging.getLogger("fastflix")
ffmpeg_folder = Path(user_data_dir("FFmpeg", appauthor=False, roaming=True))

NO_OPT = object()


outdated_settings = ("copy",)


def get_config(portable_mode=False):
    config = os.getenv("FF_CONFIG")
    if config:
        return Path(config)
    if Path("fastflix.yaml").exists() or portable_mode:
        return Path("fastflix.yaml")
    return Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "fastflix.yaml"


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
    # Check the FFmpeg download folder (where auto-download places it)
    hdr10plus_in_ffmpeg = ffmpeg_folder / "hdr10plus_tool.exe"
    if hdr10plus_in_ffmpeg.exists():
        return hdr10plus_in_ffmpeg
    return None


def where(filename: str, portable_mode=False) -> Path | None:
    if location := shutil.which(filename):
        return Path(location)
    if portable_mode:
        if (location := Path(filename)).exists():
            return location
    return None


def find_ocr_tool(name):
    """Find OCR tools (tesseract, mkvmerge, pgsrip) similar to how we find FFmpeg"""
    # Check environment variable
    if ocr_location := os.getenv(f"FF_{name.upper()}"):
        return Path(ocr_location).absolute()

    # Check system PATH
    if (ocr_location := shutil.which(name)) is not None:
        return Path(ocr_location).absolute()

    # Special handling for tesseract on Windows (not in PATH by default)
    if name == "tesseract" and win_based:
        # Check common install locations using environment variables
        localappdata = os.getenv("LOCALAPPDATA")
        appdata = os.getenv("APPDATA")
        program_files = os.getenv("PROGRAMFILES")
        program_files_x86 = os.getenv("PROGRAMFILES(X86)")

        # Check for Subtitle Edit's Tesseract installations and find the newest version
        subtitle_edit_versions = []
        if appdata:
            subtitle_edit_dir = Path(appdata) / "Subtitle Edit"
            if subtitle_edit_dir.exists():
                # Find all Tesseract* directories
                for tesseract_dir in subtitle_edit_dir.glob("Tesseract*"):
                    tesseract_exe = tesseract_dir / "tesseract.exe"
                    if tesseract_exe.exists():
                        # Extract version number from directory name (e.g., Tesseract550 -> 550)
                        version_str = tesseract_dir.name.replace("Tesseract", "")
                        try:
                            version = int(version_str)
                            subtitle_edit_versions.append((version, tesseract_exe))
                        except ValueError:
                            # If we can't parse version, still add it with version 0
                            subtitle_edit_versions.append((0, tesseract_exe))

        # If we found Subtitle Edit versions, return the newest one
        if subtitle_edit_versions:
            subtitle_edit_versions.sort(reverse=True)  # Sort by version descending
            return subtitle_edit_versions[0][1]

        common_paths = []
        # Check user-local installation first
        if localappdata:
            common_paths.append(Path(localappdata) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
        # Check system-wide installations
        if program_files:
            common_paths.append(Path(program_files) / "Tesseract-OCR" / "tesseract.exe")
        if program_files_x86:
            common_paths.append(Path(program_files_x86) / "Tesseract-OCR" / "tesseract.exe")

        for path in common_paths:
            if path.exists():
                return path

        # Check Windows registry for Tesseract install location
        try:
            import winreg

            # Try HKEY_LOCAL_MACHINE first (system-wide install)
            for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(root_key, r"SOFTWARE\Tesseract-OCR")
                    install_path = winreg.QueryValueEx(key, "InstallDir")[0]
                    winreg.CloseKey(key)
                    tesseract_exe = Path(install_path) / "tesseract.exe"
                    if tesseract_exe.exists():
                        return tesseract_exe
                except (FileNotFoundError, OSError):
                    pass
        except ImportError:
            pass

    # Special handling for mkvmerge on Windows
    if name == "mkvmerge" and win_based:
        # Check common install locations using environment variables
        localappdata = os.getenv("LOCALAPPDATA")
        program_files = os.getenv("PROGRAMFILES")
        program_files_x86 = os.getenv("PROGRAMFILES(X86)")

        common_paths = []
        # Check user-local installation first
        if localappdata:
            common_paths.append(Path(localappdata) / "Programs" / "MKVToolNix" / "mkvmerge.exe")
        # Check system-wide installations
        if program_files:
            common_paths.append(Path(program_files) / "MKVToolNix" / "mkvmerge.exe")
        if program_files_x86:
            common_paths.append(Path(program_files_x86) / "MKVToolNix" / "mkvmerge.exe")

        for path in common_paths:
            if path.exists():
                return path

    # Check in FastFlix OCR tools folder
    ocr_folder = Path(user_data_dir("FastFlix_OCR", appauthor=False, roaming=True))
    if ocr_folder.exists():
        for file in ocr_folder.iterdir():
            if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                return file
        # Check bin subfolder
        if (ocr_folder / "bin").exists():
            for file in (ocr_folder / "bin").iterdir():
                if file.is_file() and file.name.lower() in (name, f"{name}.exe"):
                    return file


def find_rigaya_encoder(base_name: str) -> Path | None:
    """Find Rigaya encoder binaries with case-insensitive search."""
    # Try common binary names in order of preference
    candidates = [
        f"{base_name}64",  # Windows 64-bit
        f"{base_name}",  # Windows/Linux
        f"{base_name.lower()}",  # Linux lowercase
    ]

    for candidate in candidates:
        if location := where(candidate):
            return location


class Config(BaseModel):
    version: str = __version__
    config_path: Path = Field(default_factory=get_config)
    ffmpeg: Path = Field(default_factory=lambda: find_ffmpeg_file("ffmpeg"))
    ffprobe: Path = Field(default_factory=lambda: find_ffmpeg_file("ffprobe"))
    hdr10plus_parser: Path | None = Field(default_factory=find_hdr10plus_tool)
    nvencc: Path | None = Field(default_factory=lambda: find_rigaya_encoder("NVEncC"))
    vceencc: Path | None = Field(default_factory=lambda: find_rigaya_encoder("VCEEncC"))
    qsvencc: Path | None = Field(default_factory=lambda: find_rigaya_encoder("QSVEncC"))
    gifski: Path | None = Field(default_factory=lambda: where("gifski"))
    output_directory: Path | None = None
    source_directory: Path | None = None
    output_name_format: str = "{source}-fastflix-{rand_4}"
    flat_ui: bool = True
    language: str = "eng"
    logging_level: int = 10
    crop_detect_points: int = 10
    continue_on_failure: bool = True
    work_path: Path = Path(os.getenv("FF_WORKDIR", user_data_dir("FastFlix", appauthor=False, roaming=True)))
    use_sane_audio: bool = True
    selected_profile: str = "Standard Profile"
    theme: str = "onyx"
    disable_version_check: bool = False
    disable_update_check: bool = False  # old name
    disable_automatic_subtitle_burn_in: bool = False
    custom_after_run_scripts: dict = Field(default_factory=dict)
    profiles: dict[str, Profile] = Field(default_factory=get_preset_defaults)
    priority: Literal["Realtime", "High", "Above Normal", "Normal", "Below Normal", "Idle"] = "Normal"
    disable_deinterlace_check: bool = False
    stay_on_top: bool = False
    portable_mode: bool = False
    ui_scale: str = "1"
    clean_old_logs: bool = True
    auto_gpu_check: bool | None = None
    auto_hdr10plus_check: bool | None = None
    gpu_fingerprint: str | None = None
    opencl_support: bool | None = None
    seven_zip: Path | None = None
    sane_audio_selection: list = Field(
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
    vceencc_encoders: list = Field(default_factory=list)
    qsvencc_encoders: list = Field(default_factory=list)
    nvencc_encoders: list = Field(default_factory=list)

    vceencc_devices: dict = Field(default_factory=dict)
    qsvencc_devices: dict = Field(default_factory=dict)
    nvencc_devices: dict = Field(default_factory=dict)

    sticky_tabs: bool = False
    disable_complete_message: bool = False

    disable_cover_extraction: bool = False

    # PGS to SRT OCR Settings
    enable_pgs_ocr: bool = False
    tesseract_path: Path | None = Field(default_factory=lambda: find_ocr_tool("tesseract"))
    mkvmerge_path: Path | None = Field(default_factory=lambda: find_ocr_tool("mkvmerge"))
    pgs_ocr_language: str = "eng"

    use_keyframes_for_preview: bool = True

    @property
    def pgs_ocr_available(self) -> bool:
        import importlib.util

        return self.tesseract_path is not None and importlib.util.find_spec("pgsrip") is not None

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

    def advanced_opt(self, profile_option_name, default=NO_OPT):
        advanced_settings = getattr(self.profiles[self.selected_profile], "advanced_options")
        if default != NO_OPT:
            return getattr(advanced_settings, profile_option_name, default)
        return getattr(advanced_settings, profile_option_name)

    def profile_v1_to_v2(self, name, raw_profile):
        logger.info(f'Upgrading profile "{name}" to version 2')
        try:
            audio_language = raw_profile.pop("audio_language")
        except KeyError:
            audio_language = "en"

        try:
            audio_select = raw_profile.pop("audio_select")
        except KeyError:
            audio_select = False

        try:
            audio_select_preferred_language = raw_profile.pop("audio_select_preferred_language")
        except KeyError:
            audio_select_preferred_language = False

        try:
            audio_select_first_matching = raw_profile.pop("audio_select_first_matching")
        except KeyError:
            audio_select_first_matching = False

        try:
            del raw_profile["profile_version"]
        except KeyError:
            pass

        try:
            del raw_profile["audio_filters"]
        except KeyError:
            pass

        if audio_select:
            new_match = AudioMatch(
                match_type=MatchType.FIRST if audio_select_first_matching else MatchType.ALL,
                match_item=MatchItem.LANGUAGE if audio_select_preferred_language else MatchItem.ALL,
                match_input=audio_language if audio_select_preferred_language else "*",
            )

            return Profile(profile_version=2, audio_filters=[new_match], **raw_profile)
        return Profile(profile_version=2, **raw_profile)

    def pre_load(self, portable_mode=False):
        """Used before application startup to see if there are any QT variables we need to set"""
        self.config_path = get_config(portable_mode=portable_mode)
        try:
            data = Box.from_yaml(filename=self.config_path)
        except Exception:
            data = Box()

        output = {"enable_scaling": True}

        if "ui_scale" in data:
            scale = str(data["ui_scale"])
            if scale not in ("0", "1"):
                os.putenv("QT_SCALE_FACTOR", scale)
            if scale == "0":
                output["enable_scaling"] = False
        return output

    def load(self, portable_mode=False):
        self.portable_mode = portable_mode
        self.config_path = get_config(portable_mode=portable_mode)
        if portable_mode:
            self.work_path = Path(os.getenv("FF_WORKDIR", "fastflix_workspace"))
            self.work_path.mkdir(exist_ok=True)

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

        if version.parse(__version__) < version.parse(data.version):
            logger.warning(
                f"This FastFlix version ({__version__}) is older "
                f"than the one that generated the config file ({data.version}), "
                "there may be non-recoverable errors while loading it."
            )

        paths = (
            "work_path",
            "ffmpeg",
            "ffprobe",
            "hdr10plus_parser",
            "nvencc",
            "output_directory",
            "source_directory",
            "seven_zip",
            "vceencc",
            "qsvencc",
            "gifski",
        )
        for key, value in data.items():
            if key == "profiles":
                self.profiles = {}
                for k, v in value.items():
                    if v.get("profile_version", 1) == 1:
                        self.profiles[k] = self.profile_v1_to_v2(k, v)
                    else:
                        self.profiles[k] = Profile(**v)
                continue
            if key in self and key not in ("config_path", "version"):
                setattr(self, key, Path(value) if key in paths and value else value)

        if self.output_directory is False:
            self.output_directory = None

        if self.source_directory is False:
            self.source_directory = None

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
            self.hdr10plus_parser = find_hdr10plus_tool()
        if not self.nvencc:
            self.nvencc = where("NVEncC64", portable_mode=portable_mode) or where("NVEncC", portable_mode=portable_mode)
        if not self.vceencc:
            self.vceencc = where("VCEEncC64", portable_mode=portable_mode) or where(
                "VCEEncC", portable_mode=portable_mode
            )
        if not self.qsvencc:
            self.qsvencc = where("QSVEncC64", portable_mode=portable_mode) or where(
                "QSVEncC", portable_mode=portable_mode
            )
        if not self.gifski:
            self.gifski = where("gifski", portable_mode=portable_mode)
        if not self.gifski and win_based:
            cargo_bin_path = Path(os.environ.get("USERPROFILE", "")) / ".cargo" / "bin" / "gifski.exe"
            if cargo_bin_path.exists():
                self.gifski = cargo_bin_path
        self.profiles.update(get_preset_defaults())

        if self.selected_profile not in self.profiles:
            self.selected_profile = "Standard Profile"

        # 5.2.0 remove ext
        self.output_name_format = self.output_name_format.replace(".{ext}", "").replace("{ext}", "")
        # if version.parse(__version__) > version.parse(data.version):
        #     logger.info(f"Clearing possible old config values from fastflix {data.version}")
        #     self.vceencc_encoders = []
        #     self.nvencc_encoders = []
        #     self.qsvencc_encoders = []

        # self.check_hw_encoders()

    def check_hw_encoders(self):
        if self.nvencc:
            logger.info("Checking for available NVEncC encoders")
            try:
                self.nvencc_devices, self.nvencc_encoders = get_all_encoder_formats_and_devices(
                    self.nvencc, is_nvenc=True
                )
            except Exception:
                logger.exception("Errored while checking for available NVEncC formats")
        else:
            self.nvencc_encoders = []
        if self.vceencc:
            logger.info("Checking for available VCEEncC encoders")
            try:
                self.vceencc_devices, self.vceencc_encoders = get_all_encoder_formats_and_devices(
                    self.vceencc, is_vce=True
                )
            except Exception:
                logger.exception("Errored while checking for available VCEEncC formats")
        else:
            self.vceencc_encoders = []
        if self.qsvencc:
            logger.info("Checking for available QSVEncC encoders")
            try:
                self.qsvencc_devices, self.qsvencc_encoders = get_all_encoder_formats_and_devices(
                    self.qsvencc, is_qsv=True
                )
            except Exception:
                logger.exception("Errored while checking for available QSVEncC formats")
        else:
            self.qsvencc_encoders = []

    def save(self):
        items = self.model_dump()
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
            self.disable_version_check = data.get("disable_update_check", self.disable_update_check)
            self.disable_version_check = data.get("disable_version_check", self.disable_version_check)
            self.use_sane_audio = data.get("use_sane_audio")
            for audio_type in data.get("sane_audio_selection", []):
                if audio_type not in self.sane_audio_selection:
                    self.sane_audio_selection.append(audio_type)
            self.save()
            old_config_path.unlink(missing_ok=True)
            return True
        return False
