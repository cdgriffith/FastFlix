#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from fastflix.version import __version__

now = dt.now().strftime("%Y.%m.%d-%H.%M")


def write_and_exit(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    if sys.argv[1] == "exact":
        write_and_exit(__version__)
    elif sys.argv[1] == "nsis":
        write_and_exit(f"{__version__}.0")

    branch = os.getenv("GITHUB_REF").rsplit("/", 1)[1]

    if branch == "master":
        write_and_exit(__version__)
    else:
        write_and_exit(f"{__version__}-{branch}-{now}")
