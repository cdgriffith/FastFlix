# -*- coding: utf-8 -*-
from pathlib import Path

import pkg_resources

main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
default_mode = Path(pkg_resources.resource_filename(__name__, "data/styles/default.qss")).resolve().read_text()


changes_file = Path(pkg_resources.resource_filename(__name__, "CHANGES")).resolve()
local_changes_file = Path(__file__).parent.parent / "CHANGES"

loading_movie = str(Path(pkg_resources.resource_filename(__name__, "data/icons/loading.gif")).resolve())


def get_icon(name: str, theme: str):
    folder = "black"
    if theme.lower() in ("dark", "onyx"):
        folder = "white"
    if theme == "selected":
        folder = "selected"
    location = Path(pkg_resources.resource_filename(__name__, f"data/icons/{folder}/{name}.png")).resolve()
    if not location.exists():
        raise Exception(f"Cannot find: {location}")
    return str(location)


def group_box_style(pt="-10px", pb="5px", mt="5px", mb="0", bb="1px solid #bab9b8"):
    return f"QGroupBox{{padding-top: {pt}; padding-bottom: {pb}; margin-bottom: {mb}; margin-top: {mt}; border: none; border-bottom: {bb}; border-radius: 0; }}"


reset_button_style = "QPushButton{border: none; margin-left: 0; padding-left: 0; margin-top: 0;}"
