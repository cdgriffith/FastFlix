#!/usr/bin/env python

import shutil

from flix.version import __version__

dest = f'C:\\Users\\teckc\\AppData\\Roaming\\FastFlix\\{__version__}\\plugins'

shutil.rmtree(dest, ignore_errors=True)
shutil.copytree('flix\\plugins', dest)