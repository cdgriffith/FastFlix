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


if os.getenv("GITHUB_ACTIONS"):
    branch = os.getenv("GITHUB_REF").rsplit("/", 1)[1]

    if branch == "master":
        write_and_exit(__version__)
    else:
        write_and_exit(f"{__version__}-{branch}-{now}")

else:
    build_id = os.getenv("APPVEYOR_BUILD_ID")
    branch = os.getenv("APPVEYOR_REPO_BRANCH", "none")
    pr_branch = os.getenv("APPVEYOR_PULL_REQUEST_HEAD_REPO_BRANCH")
    pr_number = os.getenv("APPVEYOR_PULL_REQUEST_NUMBER")

    if not pr_branch and branch == "master":
        write_and_exit(__version__)

    elif pr_branch:
        write_and_exit(f"{__version__}-pr-{pr_number}-{now}")

    else:
        write_and_exit(f"{__version__}-{branch}-{now}")
