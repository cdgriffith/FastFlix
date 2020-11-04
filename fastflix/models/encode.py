# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union
from tempfile import TemporaryDirectory

from appdirs import user_data_dir
from box import Box

from fastflix.models.base import BaseDataClass


@dataclass
class AudioTrack(BaseDataClass):
    index: int
    outdex: int
    codec: str = ""
    downmix: int = 0
    title: str = ""
    language: str = ""
    conversion_bitrate: str = ""
    conversion_codec: str = ""


@dataclass
class SubtitleTrack(BaseDataClass):
    index: int
    outdex: int
    disposition: str = ""
    burn_in: bool = False
    language: str = ""
