# -*- coding: utf-8 -*-

import re
from distutils.version import StrictVersion

import requests
from box import Box


def test_version():
    with open("fastflix/version.py") as version_file:
        code_version = StrictVersion(re.search(r"__version__ *= *['\"](.+)['\"]", version_file.read()).group(1))

    pyproject_version = StrictVersion(Box.from_toml(filename="pyproject.toml").tool.poetry.version)

    assert code_version == pyproject_version, f"Code Version {code_version} vs PyProject Version {pyproject_version}"

    url = "https://api.github.com/repos/cdgriffith/FastFlix/releases/latest"
    data = requests.get(url).json()
    assert (
        StrictVersion(data["tag_name"]) < code_version
    ), f"Last Release Version {StrictVersion(data['tag_name'])} vs Code Version {code_version}"
