# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union, List
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


@dataclass
class EncoderSettings(BaseDataClass):
    name: str
    remove_hdr: bool = False


@dataclass
class x265Settings(EncoderSettings):
    preset: str = ""
    intra_encoding: bool = False
    max_mux: str = "1024"
    pix_fmt: str = ""
    profile: str = ""
    hdr10: bool = False
    hdr10_opt: bool = False
    repeat_headers: bool = False
    aq_mode: int = 2
    hdr10plus_metadata: str = ""
    crf: Union[int, None] = None
    bitrate: Union[str, None] = None
    tune: Union[str, None] = None
    x265_params: List[str] = field(default_factory=[])
