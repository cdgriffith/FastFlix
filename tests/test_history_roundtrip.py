#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test that encoder settings survive a model_dump() → reconstruct round-trip,
which is the path used by history apply-settings."""

import pytest

from fastflix.models.encode import CopySettings, SVTAV1Settings, x265Settings


@pytest.mark.parametrize(
    "settings_class,overrides",
    [
        (x265Settings, {}),
        (x265Settings, {"crf": 18, "preset": "slow", "x265_params": ["aq-mode=3", "psy-rd=1.5"]}),
        (SVTAV1Settings, {}),
        (SVTAV1Settings, {"qp": 30, "speed": "4", "svtav1_params": ["tune=0"], "film_grain": 8}),
        (CopySettings, {}),
    ],
    ids=["x265-default", "x265-custom", "svtav1-default", "svtav1-custom", "copy-default"],
)
def test_settings_roundtrip(settings_class, overrides):
    original = settings_class(**overrides)
    dumped = original.model_dump()
    restored = settings_class(**dumped)
    assert restored == original
    assert restored.model_dump() == dumped
