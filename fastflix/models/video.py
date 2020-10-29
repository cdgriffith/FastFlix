# -*- coding: utf-8 -*-
from pathlib import Path
from dataclasses import dataclass
from typing import Union, Any

from appdirs import user_data_dir
from box import Box


class ValidDataClass:
    def __setattr__(self, key, value):
        if value is not None and key in self.__class__.__annotations__:
            annotation = self.__class__.__annotations__[key]
            if hasattr(annotation, "__args__"):
                annotation = annotation.__args__
            elif hasattr(annotation, "_name"):
                # Assuming this is a typing object we can't handle
                return super().__setattr__(key, value)
            try:
                if not isinstance(value, annotation):
                    raise ValueError(f'"{key}" attempted to be set to "{value}" but must be of type "{annotation}"')
            except TypeError as err:
                print(f"Could not validate type for {key}: {err}")
        return super().__setattr__(key, value)


@dataclass
class VideoSettings(ValidDataClass):
    crop: str = None
    end_time: float = None
    start_time: Union[float, int] = 0
    fast_seek: Any = True
    rotate: str = None
    vertical_flip: bool = False
    horizontal_flip: bool = False
    remove_metadata: bool = True
    copy_chapters: bool = True
    video_title: str = None


@dataclass
class Video(ValidDataClass):
    source: Path
    width: int
    height: int
    duration: Union[float, int]
    colorspace: str = None
    output_path: Path = None
    streams: dict = None
    bit_depth: int = 8
    video_settings: VideoSettings = None
