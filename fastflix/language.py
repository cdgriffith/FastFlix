# -*- coding: utf-8 -*-
"""
gettext is an antique that uses a horrid folder structure,
proprietary format, and requires checking in binary files to git.

So here is an easy stand-in that is better in ways I care about.
"""

from box import Box

from fastflix.resources import language_file

__all__ = ["change_language", "t"]

language = "en"
language_data = Box.from_yaml(filename=language_file)


def t(text):
    if text in language_data:
        if language in language_data[text]:
            return language_data[text][language]
    return text


def change_language(lang):
    global language
    language = lang
