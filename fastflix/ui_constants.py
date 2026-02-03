# -*- coding: utf-8 -*-
"""
UI Constants for FastFlix.

Defines base dimensions for UI elements at the reference resolution of 1200x680.
These values are used with the UIScaler to compute actual pixel sizes at runtime.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaseWidths:
    """Base width values (~25% smaller than original for better default scaling)."""

    MENUBAR: int = 270
    PROFILE_BOX: int = 190
    ENCODER_MIN: int = 165
    CROP_BOX_MIN: int = 280
    SOURCE_LABEL: int = 65
    RESOLUTION_CUSTOM: int = 115
    FLIP_DROPDOWN: int = 120
    ROTATE_DROPDOWN: int = 130
    PREVIEW_MIN: int = 330
    OUTPUT_TYPE: int = 60
    VIDEO_TRACK_LABEL: int = 75
    ENCODER_LABEL: int = 50
    RESOLUTION_LABEL: int = 70
    FAST_TIME: int = 50
    AUTO_CROP: int = 40
    RESET_BUTTON: int = 12
    SMALL_BUTTON: int = 15
    AUDIO_TITLE: int = 115
    AUDIO_INFO: int = 265
    SPACER_SMALL: int = 3
    CUSTOM_INPUT: int = 75


@dataclass(frozen=True, slots=True)
class BaseHeights:
    """Base height values (~25% smaller than original for better default scaling)."""

    TOP_BAR_BUTTON: int = 38
    PATH_WIDGET: int = 20
    COMBO_BOX: int = 22
    PANEL_ITEM: int = 62
    SCROLL_MIN: int = 150
    PREVIEW_MIN: int = 195
    OUTPUT_DIR: int = 18
    HEADER: int = 23
    SPACER_TINY: int = 2
    SPACER_SMALL: int = 4
    BUTTON_SIZE: int = 22


@dataclass(frozen=True, slots=True)
class BaseIconSizes:
    """Base icon sizes (square) - ~25% smaller than original."""

    TINY: int = 8
    SMALL: int = 12
    MEDIUM: int = 17
    LARGE: int = 20
    XLARGE: int = 26


@dataclass(frozen=True, slots=True)
class BaseFontSizes:
    """Base font sizes."""

    SMALL: int = 9
    NORMAL: int = 10
    MEDIUM: int = 11
    LARGE: int = 12
    XLARGE: int = 14


WIDTHS = BaseWidths()
HEIGHTS = BaseHeights()
ICONS = BaseIconSizes()
FONTS = BaseFontSizes()
