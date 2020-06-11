#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import os
from appdirs import user_data_dir
from pathlib import Path

from flix.version import __version__

data_path = Path(user_data_dir("FastFlix", appauthor=False, version=__version__, roaming=True))
data_path.mkdir(parents=True, exist_ok=True)


dest = f"{data_path}{os.sep}plugins"

print(f"Copying plugins to {dest}")

shutil.rmtree(dest, ignore_errors=True)
shutil.copytree(f"flix{os.sep}plugins", dest)
