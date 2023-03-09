# -*- coding: utf-8 -*-
from pathlib import Path
import os
from functools import lru_cache

import importlib.resources

ref = importlib.resources.files("fastflix") / "data/icon.ico"
with importlib.resources.as_file(ref) as icon_file:
    main_icon = str(icon_file.resolve())

ref = importlib.resources.files("fastflix") / "CHANGES"
with importlib.resources.as_file(ref) as cf:
    changes_file = cf.resolve()
local_changes_file = Path(__file__).parent.parent / "CHANGES"
local_package_changes_file = Path(__file__).parent / "CHANGES"

ref = importlib.resources.files("fastflix") / "data/icons/loading.gif"
with importlib.resources.as_file(ref) as icon_file:
    loading_movie = str(icon_file.resolve())

ref = importlib.resources.files("fastflix") / "data/icons/onyx-convert.svg"
with importlib.resources.as_file(ref) as icon_file:
    onyx_convert_icon = str(icon_file.resolve())

ref = importlib.resources.files("fastflix") / "data/icons/onyx-add-queue.svg"
with importlib.resources.as_file(ref) as icon_file:
    onyx_queue_add_icon = str(icon_file.resolve())

ref = importlib.resources.files("fastflix") / "data/styles/breeze_styles"
with importlib.resources.as_file(ref) as bf:
    breeze_styles_path = bf.resolve()


# fmt: off
video_file_types = ('.mkv', '.mp4', '.m4v', '.mov', '.avi', '.divx', '.webm', '.mpg', '.mp2', '.mpeg', '.mpe', '.mpv',
                    '.ogg', '.m4p', '.wmv', '.mov', '.qt', '.flv', '.hevc', '.gif', '.webp', '.vob', '.ogv', '.ts',
                    '.mts', '.m2ts', '.yuv', '.rm', '.svi', '.3gp', '.3g2', '.y4m')
# fmt: on


@lru_cache()
def get_icon(name: str, theme: str):
    folder = "black"
    if theme.lower() in ("dark", "onyx"):
        folder = "white"
    if theme == "selected":  # Used for bright tab colors
        folder = "selected"

    ref = importlib.resources.files("fastflix") / f"data/icons/{folder}/{name}.svg"
    with importlib.resources.as_file(ref) as icon_file:
        location = icon_file.resolve()

    if not location.exists():
        ref = importlib.resources.files("fastflix") / f"data/icons/{folder}/{name}.png"
        with importlib.resources.as_file(ref) as icon_file:
            location = icon_file.resolve()

    if not location.exists():
        raise Exception(f"Cannot find: {location}")
    return str(location)


def get_text_color(theme: str):
    if theme.lower() == "dark":
        return "255, 255, 255"
    return "0, 0, 0"


def group_box_style(pt="-10px", pb="5px", mt="5px", mb="0", bb="1px solid #bab9b8"):
    return (
        f"QGroupBox{{padding-top: {pt}; padding-bottom: {pb}; margin-bottom: {mb}; "
        f"margin-top: {mt}; border: none; border-bottom: {bb}; border-radius: 0; }}"
    )


reset_button_style = "QPushButton{border: none; margin-left: 0; padding-left: 0; margin-top: 0;}"


def get_bool_env(variable: str):
    var = os.getenv(variable, "")
    if not var:
        return False
    if var.lower() in ("1", "on", "yes", "true", "t"):
        return True
    return False
