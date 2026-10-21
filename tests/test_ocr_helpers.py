# -*- coding: utf-8 -*-
import pytest

from fastflix.widgets.background_tasks import pgsrip_srt_path, resolve_babel_language


@pytest.mark.parametrize(
    "code,alpha2",
    [
        ("fre", "fr"),
        ("ger", "de"),
        ("chi", "zh"),
        ("eng", "en"),
        ("fra", "fr"),
        ("deu", "de"),
        ("zho", "zh"),
        ("und", "und"),
        ("fr", "fr"),
        ("EN", "en"),
    ],
)
def test_resolve_babel_language(code, alpha2):
    assert str(resolve_babel_language(code)) == alpha2


def test_resolve_babel_language_name_and_garbage():
    assert str(resolve_babel_language("French")) == "fr"
    assert str(resolve_babel_language("zzzzz")) == "en"
    assert str(resolve_babel_language("")) == "en"


def test_pgsrip_srt_path(tmp_path):
    assert pgsrip_srt_path(tmp_path / "movie.en.sup") == tmp_path / "movie.en.srt"
