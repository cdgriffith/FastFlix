# -*- coding: utf-8 -*-
from subprocess import run, PIPE
import re
from packaging import version

import requests


def test_version():
    with open("fastflix/version.py") as version_file:
        code_version = version.parse(re.search(r"__version__ *= *['\"](.+)['\"]", version_file.read()).group(1))

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases/latest"
    data = requests.get(url).json()
    assert (
        version.parse(data["tag_name"]) < code_version
    ), f"Last Release Version {version.parse(data['tag_name'])} vs Code Version {code_version}"
