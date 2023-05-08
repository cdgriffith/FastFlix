# -*- coding: utf-8 -*-
"""
gettext is an antique that uses a horrid folder structure,
proprietary format, and requires checking in binary files to git.

So here is an easy stand-in that is better in ways I care about.
"""
import os
from functools import lru_cache
from pathlib import Path
import importlib.resources

from appdirs import user_data_dir
from box import Box

ref = importlib.resources.files("fastflix") / "data/languages.yaml"
with importlib.resources.as_file(ref) as lf:
    language_file = str(lf.resolve())


__all__ = ["t", "translate"]

config = os.getenv("FF_CONFIG")
if config:
    config = Path(config)
elif Path("fastflix.yaml").exists():
    config = Path("fastflix.yaml")
else:
    config = Path(user_data_dir("FastFlix", appauthor=False, roaming=True)) / "fastflix.yaml"

language = os.getenv("FF_LANG")

if not language:
    try:
        language = Box.from_yaml(filename=config).language
    except Exception as err:
        if not str(err).endswith("does not exist"):
            print("WARNING: Could not get language from config file")
        language = "eng"

language_data = Box.from_yaml(filename=language_file, encoding="utf-8")

if language not in ("deu", "eng", "fra", "ita", "spa", "chs", "rus", "jpn", "pol", "swe", "por", "ukr", "kor", "ron"):
    print(f"WARNING: {language} is not a supported language, defaulting to eng")
    language = "eng"


@lru_cache(maxsize=2048)  # This little trick makes re-calls 10x faster
def translate(text):
    if text in language_data:
        if language in language_data[text]:
            return language_data[text][language]
    else:
        if os.getenv("DEVMODE", "").lower() in ("1", "true"):
            print(f'Cannot find translation for: "{text}"')
    return text


t = translate
