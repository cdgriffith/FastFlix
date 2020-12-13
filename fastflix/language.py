# -*- coding: utf-8 -*-
"""
gettext is an antique that uses a horrid folder structure,
proprietary format, and requires checking in binary files to git.

So here is an easy stand-in that is better in ways I care about.
"""
from functools import lru_cache
from pathlib import Path

from box import Box
from iso639 import Lang
from appdirs import user_data_dir

from fastflix.resources import language_file

__all__ = ["t", "translate"]

config = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "fastflix.yaml"

try:
    language = Box.from_yaml(filename=config).language
except Exception:
    print("WARNING: Could not get language from config file")
    language = "eng"

language_data = Box.from_yaml(filename=language_file, encoding="utf-8")


@lru_cache(maxsize=512)  # This little trick makes re-calls 10x faster
def translate(text):
    if text in language_data:
        if language in language_data[text]:
            return language_data[text][language]
    # else:
    #     language_data[text] = {"eng": text}
    #     language_data.to_yaml(filename=language_file, encoding="utf-8", width=400)
    return text


t = translate
