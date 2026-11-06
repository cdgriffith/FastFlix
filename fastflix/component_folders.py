# -*- coding: utf-8 -*-
"""Where downloaded components (FFmpeg, NVEnc, hdr10plus_tool, ...) are stored and searched for.

By default every component lives in its own AppData folder. The user can set a single "Components folder"
in the settings; downloads then go to <components folder>/<name>, and lookups check that folder first and
the AppData folder second.
"""

from pathlib import Path

from platformdirs import user_data_dir

_components_dir: Path | None = None


def set_components_dir(path: Path | str | None) -> None:
    global _components_dir
    _components_dir = Path(path) if path else None


def get_components_dir() -> Path | None:
    return _components_dir


def default_component_folder(name: str) -> Path:
    return Path(user_data_dir(name, appauthor=False, roaming=True))


def component_folder(name: str) -> Path:
    """Folder new downloads of the named component are written to."""
    if _components_dir is not None:
        return _components_dir / name
    return default_component_folder(name)


def component_search_folders(name: str) -> list[Path]:
    """Folders to search for the named component, most preferred first."""
    folders = [component_folder(name)]
    default = default_component_folder(name)
    if default not in folders:
        folders.append(default)
    return folders
