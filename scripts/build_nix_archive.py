# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import shutil
from subprocess import check_output
import platform
import reusables

from fastflix.version import __version__

arch = "arm64" if "arm64" in platform.platform() else "x86_64"

here = Path(__file__).parent
dist_folder = Path(here.parent / "dist")

reusables.archive(
    [x for x in dist_folder.rglob("*")],
    name=str(dist_folder / f"FastFlix_{__version__}_{sys.argv[1]}_{arch}.zip"),
    archive_type="zip",
)
