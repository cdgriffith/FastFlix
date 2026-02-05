#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from fastflix.version import __version__

now = dt.now().strftime("%Y.%m.%d-%H.%M")


def write_and_exit(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sys.exit(0)


def get_nsis_version(version: str) -> str:
    """
    Convert a PEP 440 version string to NSIS-compatible X.X.X.X format.

    NSIS VIProductVersion/VIFileVersion require exactly 4 numeric components.
    Examples:
        5.13.0 -> 5.13.0.0
        5.13.0b1 -> 5.13.0.1
        5.13.0a2 -> 5.13.0.2
        5.13.0rc3 -> 5.13.0.3
    """
    # Match: major.minor.patch followed by optional pre-release (a/b/rc + number)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)(\d+))?", version)
    if match:
        major, minor, patch, prerelease = match.groups()
        prerelease_num = prerelease if prerelease else "0"
        return f"{major}.{minor}.{patch}.{prerelease_num}"
    # Fallback: just append .0
    return f"{version}.0"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "exact":
            write_and_exit(__version__)
        elif sys.argv[1] == "nsis":
            write_and_exit(get_nsis_version(__version__))

    branch = os.getenv("GITHUB_REF").rsplit("/", 1)[1]

    if branch == "master":
        write_and_exit(__version__)
    else:
        write_and_exit(f"{__version__}-{branch}-{now}")
