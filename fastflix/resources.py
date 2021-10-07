# -*- coding: utf-8 -*-
from pathlib import Path
import os

import pkg_resources

main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
default_mode = Path(pkg_resources.resource_filename(__name__, "data/styles/default.qss")).resolve().read_text()

changes_file = Path(pkg_resources.resource_filename(__name__, "CHANGES")).resolve()
local_changes_file = Path(__file__).parent.parent / "CHANGES"

loading_movie = str(Path(pkg_resources.resource_filename(__name__, "data/icons/loading.gif")).resolve())
onyx_convert_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/onyx-convert.png")).resolve())
onyx_queue_add_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/onyx-add-queue.png")).resolve())

breeze_styles_path = Path(pkg_resources.resource_filename(__name__, "data/styles/breeze_styles")).resolve()


def get_icon(name: str, theme: str):
    folder = "black"
    if theme.lower() in ("dark", "onyx"):
        folder = "white"
    if theme == "selected":  # Used for bright tab colors
        folder = "selected"
    location = Path(pkg_resources.resource_filename(__name__, f"data/icons/{folder}/{name}.png")).resolve()
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
