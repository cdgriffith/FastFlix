# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import shutil
from subprocess import check_output

from fastflix.version import __version__

here = Path(__file__).parent
plist_template = here.parent / "fastflix" / "data" / "Info.plist.template"

build_folder = Path(here.parent / "dist" / "FastFlix.app")
build_folder.mkdir(exist_ok=True)

content_folder = build_folder / "Contents"
content_folder.mkdir(exist_ok=True)

macos_folder = content_folder / "MacOS"
macos_folder.mkdir(exist_ok=True)

resources_folder = content_folder / "Resources"
resources_folder.mkdir(exist_ok=True)

try:
    mac_version = f"{sys.argv[1].split("-")[1]}.0"
    assert mac_version in ("12.0", "13.0", "14.0", "15.0")
except Exception:
    print(f"Did not get expected input, received: {sys.argv}")
    sys.exit(1)

with open(plist_template) as in_file, open(content_folder / "Info.plist", "w") as out_file:
    template = in_file.read().format(version=__version__, mac_version=mac_version)
    out_file.write(template)

shutil.copy(here.parent / "fastflix" / "data" / "icon.icns", resources_folder / "icon.icns")

shutil.move(here.parent / "dist" / "FastFlix", macos_folder / "FastFlix")
shutil.move(here.parent / "dist" / "LICENSE", macos_folder / "LICENSE")

check_output(["chmod", "+x", macos_folder / "FastFlix"])
