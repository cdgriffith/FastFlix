#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
from pathlib import Path
from typing import Literal
import json
import sys

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
from fastflix.models.profiles import Profile, AudioMatch, MatchItem, MatchType
from fastflix.version import __version__
from fastflix.rigaya_helpers import get_all_encoder_formats_and_devices


"""Provides classes to represent module version numbers (one class for
each style of version numbering).  There are currently two such classes
implemented: StrictVersion and LooseVersion.

Every version number class implements the following interface:
  * the 'parse' method takes a string and parses it to some internal
    representation; if the string is an invalid version number,
    'parse' raises a ValueError exception
  * the class constructor takes an optional string argument which,
    if supplied, is passed to 'parse'
  * __str__ reconstructs the string that was passed to 'parse' (or
    an equivalent string -- ie. one that will generate an equivalent
    version number instance)
  * __repr__ generates Python code to recreate the version number instance
  * __cmp__ compares the current instance with either another instance
    of the same class or a string (which will be parsed to an instance
    of the same class, thus must follow the same rules)
"""

import string, re
from types import StringType

class Version:
    """Abstract base class for version numbering classes.  Just provides
    constructor (__init__) and reproducer (__repr__), because those
    seem to be the same for all version numbering classes.
    """

    def __init__ (self, vstring=None):
        if vstring:
            self.parse(vstring)

    def __repr__ (self):
        return "%s ('%s')" % (self.__class__.__name__, str(self))


# Interface for version-number classes -- must be implemented
# by the following classes (the concrete ones -- Version should
# be treated as an abstract class).
#    __init__ (string) - create and take same action as 'parse'
#                        (string parameter is optional)
#    parse (string)    - convert a string representation to whatever
#                        internal representation is appropriate for
#                        this style of version numbering
#    __str__ (self)    - convert back to a string; should be very similar
#                        (if not identical to) the string supplied to parse
#    __repr__ (self)   - generate Python code to recreate
#                        the instance
#    __cmp__ (self, other) - compare two version numbers ('other' may
#                        be an unparsed version string, or another
#                        instance of your version class)


class StrictVersion (Version):

    """Version numbering for anal retentives and software idealists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of two or three
    dot-separated numeric components, with an optional "pre-release" tag
    on the end.  The pre-release tag consists of the letter 'a' or 'b'
    followed by a number.  If the numeric components of two version
    numbers are equal, then one with a pre-release tag will always
    be deemed earlier (lesser) than one without.

    The following are valid version numbers (shown in the order that
    would be obtained by sorting according to the supplied cmp function):

        0.4       0.4.0  (these two are equivalent)
        0.4.1
        0.5a1
        0.5b3
        0.5
        0.9.6
        1.0
        1.0.4a3
        1.0.4b1
        1.0.4

    The following are examples of invalid version numbers:

        1
        2.7.2.2
        1.3.a4
        1.3pl1
        1.3c4

    The rationale for this version numbering system will be explained
    in the distutils documentation.
    """

    version_re = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$',
                            re.VERBOSE)


    def parse (self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError, "invalid version number '%s'" % vstring

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(string.atoi, [major, minor, patch]))
        else:
            self.version = tuple(map(string.atoi, [major, minor]) + [0])

        if prerelease:
            self.prerelease = (prerelease[0], string.atoi(prerelease_num))
        else:
            self.prerelease = None


    def __str__ (self):

        if self.version[2] == 0:
            vstring = string.join(map(str, self.version[0:2]), '.')
        else:
            vstring = string.join(map(str, self.version), '.')

        if self.prerelease:
            vstring = vstring + self.prerelease[0] + str(self.prerelease[1])

        return vstring


    def __cmp__ (self, other):
        if isinstance(other, StringType):
            other = StrictVersion(other)

        compare = cmp(self.version, other.version)
        if (compare == 0):              # have to compare prerelease

            # case 1: neither has prerelease; they're equal
            # case 2: self has prerelease, other doesn't; other is greater
            # case 3: self doesn't have prerelease, other does: self is greater
            # case 4: both have prerelease: must compare them!

            if (not self.prerelease and not other.prerelease):
                return 0
            elif (self.prerelease and not other.prerelease):
                return -1
            elif (not self.prerelease and other.prerelease):
                return 1
            elif (self.prerelease and other.prerelease):
                return cmp(self.prerelease, other.prerelease)

        else:                           # numeric versions don't match --
            return compare              # prerelease stuff doesn't matter


# end class StrictVersion


# The rules according to Greg Stein:
# 1) a version number has 1 or more numbers separated by a period or by
#    sequences of letters. If only periods, then these are compared
#    left-to-right to determine an ordering.
# 2) sequences of letters are part of the tuple for comparison and are
#    compared lexicographically
# 3) recognize the numeric components may have leading zeroes
#
# The LooseVersion class below implements these rules: a version number
# string is split up into a tuple of integer and string components, and
# comparison is a simple tuple comparison.  This means that version
# numbers behave in a predictable and obvious way, but a way that might
# not necessarily be how people *want* version numbers to behave.  There
# wouldn't be a problem if people could stick to purely numeric version
# numbers: just split on period and compare the numbers as tuples.
# However, people insist on putting letters into their version numbers;
# the most common purpose seems to be:
#   - indicating a "pre-release" version
#     ('alpha', 'beta', 'a', 'b', 'pre', 'p')
#   - indicating a post-release patch ('p', 'pl', 'patch')
# but of course this can't cover all version number schemes, and there's
# no way to know what a programmer means without asking him.
#
# The problem is what to do with letters (and other non-numeric
# characters) in a version number.  The current implementation does the
# obvious and predictable thing: keep them as strings and compare
# lexically within a tuple comparison.  This has the desired effect if
# an appended letter sequence implies something "post-release":
# eg. "0.99" < "0.99pl14" < "1.0", and "5.001" < "5.001m" < "5.002".
#
# However, if letters in a version number imply a pre-release version,
# the "obvious" thing isn't correct.  Eg. you would expect that
# "1.5.1" < "1.5.2a2" < "1.5.2", but under the tuple/lexical comparison
# implemented here, this just isn't so.
#
# Two possible solutions come to mind.  The first is to tie the
# comparison algorithm to a particular set of semantic rules, as has
# been done in the StrictVersion class above.  This works great as long
# as everyone can go along with bondage and discipline.  Hopefully a
# (large) subset of Python module programmers will agree that the
# particular flavour of bondage and discipline provided by StrictVersion
# provides enough benefit to be worth using, and will submit their
# version numbering scheme to its domination.  The free-thinking
# anarchists in the lot will never give in, though, and something needs
# to be done to accommodate them.
#
# Perhaps a "moderately strict" version class could be implemented that
# lets almost anything slide (syntactically), and makes some heuristic
# assumptions about non-digits in version number strings.  This could
# sink into special-case-hell, though; if I was as talented and
# idiosyncratic as Larry Wall, I'd go ahead and implement a class that
# somehow knows that "1.2.1" < "1.2.2a2" < "1.2.2" < "1.2.2pl3", and is
# just as happy dealing with things like "2g6" and "1.13++".  I don't
# think I'm smart enough to do it right though.
#
# In any case, I've coded the test suite for this module (see
# ../test/test_version.py) specifically to fail on things like comparing
# "1.2a2" and "1.2".  That's not because the *code* is doing anything
# wrong, it's because the simple, obvious design doesn't match my
# complicated, hairy expectations for real-world version numbers.  It
# would be a snap to fix the test suite to say, "Yep, LooseVersion does
# the Right Thing" (ie. the code matches the conception).  But I'd rather
# have a conception that matches common notions about version numbers.

class LooseVersion (Version):

    """Version numbering for anarchists and software realists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of a series of numbers,
    separated by either periods or strings of letters.  When comparing
    version numbers, the numeric components will be compared
    numerically, and the alphabetic components lexically.  The following
    are all valid version numbers, in no particular order:

        1.5.1
        1.5.2b2
        161
        3.10a
        8.02
        3.4j
        1996.07.12
        3.2.pl0
        3.1.1.6
        2g6
        11g
        0.960923
        2.2beta29
        1.13++
        5.5.kw
        2.0b1pl0

    In fact, there is no such thing as an invalid version number under
    this scheme; the rules for comparison are simple and predictable,
    but may not always give the results you want (for some definition
    of "want").
    """

    component_re = re.compile(r'(\d+ | [a-z]+ | \.)', re.VERBOSE)

    def __init__ (self, vstring=None):
        if vstring:
            self.parse(vstring)


    def parse (self, vstring):
        # I've given up on thinking I can reconstruct the version string
        # from the parsed tuple -- so I just store the string here for
        # use by __str__
        self.vstring = vstring
        components = filter(lambda x: x and x != '.',
                            self.component_re.split(vstring))
        for i in range(len(components)):
            try:
                components[i] = int(components[i])
            except ValueError:
                pass

        self.version = components


    def __str__ (self):
        return self.vstring


    def __repr__ (self):
        return "LooseVersion ('%s')" % str(self)


    def __cmp__ (self, other):
        if isinstance(other, StringType):
            other = LooseVersion(other)

        return cmp(self.version, other.version)


# end class LooseVersion
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
    return None


def where(filename: str, portable_mode=False) -> Path | None:
    if location := shutil.which(filename):
        return Path(location)
    if portable_mode:
        if (location := Path(filename)).exists():
            return location
    return None


class Config(BaseModel):
    version: str = __version__
    config_path: Path = Field(default_factory=get_config)
    ffmpeg: Path = Field(default_factory=lambda: find_ffmpeg_file("ffmpeg"))
    ffprobe: Path = Field(default_factory=lambda: find_ffmpeg_file("ffprobe"))
    hdr10plus_parser: Path | None = Field(default_factory=find_hdr10plus_tool)
    nvencc: Path | None = Field(default_factory=lambda: where("NVEncC64") or where("NVEncC"))
    vceencc: Path | None = Field(default_factory=lambda: where("VCEEncC64") or where("VCEEncC"))
    qsvencc: Path | None = Field(default_factory=lambda: where("QSVEncC64") or where("QSVEncC"))
    output_directory: Path | None = False
    source_directory: Path | None = False
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
    stay_on_top: bool = False
    portable_mode: bool = False
    ui_scale: str = "1"
    clean_old_logs: bool = True
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
                    if v.get("profile_version", 1) == 1:
                        self.profiles[k] = self.profile_v1_to_v2(k, v)
                    else:
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
        self.profiles.update(get_preset_defaults())

        if self.selected_profile not in self.profiles:
            self.selected_profile = "Standard Profile"

        # 5.2.0 remove ext
        self.output_name_format = self.output_name_format.replace(".{ext}", "").replace("{ext}", "")
        # if StrictVersion(__version__) > StrictVersion(data.version):
        #     logger.info(f"Clearing possible old config values from fastflix {data.verion}")
        #     self.vceencc_encoders = []
        #     self.nvencc_encoders = []
        #     self.qsvencc_encoders = []

        self.check_hw_encoders()

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
