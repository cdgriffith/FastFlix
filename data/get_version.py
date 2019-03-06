#!/usr/bin/env python

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from flix.version import __version__


def write_and_exit(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sys.exit(0)


build_id = os.getenv('APPVEYOR_BUILD_ID')
branch = os.getenv('APPVEYOR_REPO_BRANCH', 'none')
pr_branch = os.getenv('APPVEYOR_PULL_REQUEST_HEAD_REPO_BRANCH')
pr_number = os.getenv('APPVEYOR_PULL_REQUEST_NUMBER')
commit = os.getenv('APPVEYOR_REPO_COMMIT', '0000000')[:7]

if not pr_branch and branch == 'master':
    write_and_exit(__version__)

elif pr_branch:
    write_and_exit(f'{__version__}-pr-{pr_number}')

else:
    write_and_exit(f'{__version__}-{branch}-{commit}')

