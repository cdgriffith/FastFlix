#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from fastflix.widgets.windows.crop_window import CropPreviewWindow


forward = CropPreviewWindow._unrotated_to_rotated_crop
inverse = CropPreviewWindow._rotated_to_unrotated_crop

SAMPLE_CROP = {"top": 10, "right": 20, "bottom": 30, "left": 40}


def test_identity_no_transform():
    result = forward(SAMPLE_CROP, rotate=0, vflip=False, hflip=False)
    assert result == SAMPLE_CROP


@pytest.mark.parametrize("rotate", [1, 2, 3])
def test_rotation_only(rotate):
    rotated = forward(SAMPLE_CROP, rotate=rotate, vflip=False, hflip=False)
    assert rotated != SAMPLE_CROP  # rotation should change something


def test_hflip_only():
    result = forward(SAMPLE_CROP, rotate=0, vflip=False, hflip=True)
    assert result["left"] == SAMPLE_CROP["right"]
    assert result["right"] == SAMPLE_CROP["left"]
    assert result["top"] == SAMPLE_CROP["top"]
    assert result["bottom"] == SAMPLE_CROP["bottom"]


def test_vflip_only():
    result = forward(SAMPLE_CROP, rotate=0, vflip=True, hflip=False)
    assert result["top"] == SAMPLE_CROP["bottom"]
    assert result["bottom"] == SAMPLE_CROP["top"]
    assert result["left"] == SAMPLE_CROP["left"]
    assert result["right"] == SAMPLE_CROP["right"]


def test_rotation_plus_flip():
    result = forward(SAMPLE_CROP, rotate=1, vflip=False, hflip=True)
    # Just verify it returns a valid crop dict with all keys
    assert set(result.keys()) == {"top", "right", "bottom", "left"}


@pytest.mark.parametrize("rotate", [0, 1, 2, 3])
@pytest.mark.parametrize("hflip", [False, True])
@pytest.mark.parametrize("vflip", [False, True])
def test_round_trip(rotate, hflip, vflip):
    """Forward then inverse should return the original crop for all 16 combos."""
    rotated = forward(SAMPLE_CROP, rotate=rotate, vflip=vflip, hflip=hflip)
    recovered = inverse(rotated, rotate=rotate, vflip=vflip, hflip=hflip)
    assert recovered == SAMPLE_CROP, f"Round-trip failed for rotate={rotate}, hflip={hflip}, vflip={vflip}"
