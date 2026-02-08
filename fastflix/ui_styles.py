# -*- coding: utf-8 -*-
"""
UI Styles module for FastFlix.

Provides scaled stylesheets that adapt to the current UI scale factors.
"""

from fastflix.ui_scale import scaler
from fastflix.ui_constants import FONTS


# Onyx theme color constants
ONYX_COLORS = {
    "primary": "#567781",  # Blue accent (borders, selected tabs)
    "input_bg": "#4a555e",  # Input field backgrounds
    "dropdown_bg": "#4e6172",  # Dropdown backgrounds
    "text": "#ffffff",  # White text
    "text_muted": "#b5b5b5",  # Muted/disabled text
    "background": "#4f5962",  # Main background
    "overlay": "rgba(0, 0, 0, 50)",  # Overlay backgrounds
    "dark_bg": "#1d2023",  # Dark background (dropdown menus)
}


def get_scaled_stylesheet(theme: str) -> str:
    """Generate a scaled stylesheet based on the current theme and scale factors."""
    # Use pt instead of px to prevent QFont::setPointSize warnings in frozen executables.
    # Pixel-based font-size causes pointSize() to return -1, which triggers Qt warnings
    # when fonts propagate to child widgets. Convert px to pt (at 96 DPI: pt = px * 0.75).
    font_size_pt = max(6, round(scaler.scale_font(FONTS.LARGE) * 0.75))
    border_radius = scaler.scale(10)

    base = f"QWidget {{ font-size: {font_size_pt}pt; }}"

    if theme == "onyx":
        base += f"""
            QAbstractItemView {{ background-color: #4f5962; }}
            QComboBox QAbstractItemView {{ background-color: #1d2023; border: 2px solid #76797c; }}
            QPushButton {{ border-radius: {border_radius}px; }}
            QLineEdit {{
                background-color: #4a555e;
                color: white;
                border-radius: {border_radius}px;
            }}
            QTextEdit {{ background-color: #4a555e; color: white; }}
            QTabBar::tab {{ background-color: #4f5962; }}
            QComboBox {{ border-radius: {border_radius}px; }}
            QScrollArea {{ border: 1px solid #919191; }}
        """

    return base


def get_video_options_stylesheet(theme: str) -> str:
    """Generate scaled stylesheet for the video options tab widget."""
    tab_font_size_pt = max(6, round(scaler.scale_font(FONTS.MEDIUM) * 0.75))
    combo_min_height = scaler.scale(22)

    if theme == "onyx":
        return f"""
            * {{ background-color: #4f5962; color: white; }}
            QTabWidget {{ margin-top: {scaler.scale(34)}px; background-color: #4f5962; }}
            QTabBar {{ font-size: {tab_font_size_pt}pt; background-color: #4f5962; }}
            QComboBox {{ min-height: {combo_min_height}px; }}
        """
    return ""


def get_menubar_stylesheet() -> str:
    """Generate scaled stylesheet for the menu bar."""
    font_size_pt = max(6, round(scaler.scale_font(FONTS.LARGE) * 0.75))
    return f"font-size: {font_size_pt}pt"


def get_onyx_combobox_style() -> str:
    """Standard combobox/dropdown style for onyx theme."""
    return (
        f"background-color: {ONYX_COLORS['input_bg']}; "
        f"color: {ONYX_COLORS['text']}; "
        f"border: 1px solid {ONYX_COLORS['input_bg']}; "
        "border-radius: 0px;"
    )


def get_onyx_button_style() -> str:
    """Standard button style for onyx theme."""
    return (
        f"background-color: {ONYX_COLORS['input_bg']}; "
        f"color: {ONYX_COLORS['text']}; "
        f"border: 1px solid {ONYX_COLORS['input_bg']}; "
        "border-radius: 0px;"
    )


def get_onyx_disposition_style(enabled: bool = True) -> str:
    """Style for disposition dropdowns in audio/subtitle panels.

    Args:
        enabled: Whether the disposition is enabled (colored) or disabled (default)
    """
    if enabled:
        return f"border-color: {ONYX_COLORS['input_bg']}; background-color: {ONYX_COLORS['input_bg']}"
    return ""


def get_onyx_label_style(muted: bool = False) -> str:
    """Style for labels in onyx theme.

    Args:
        muted: Whether to use muted text color
    """
    color = ONYX_COLORS["text_muted"] if muted else ONYX_COLORS["text"]
    return f"color: {color}"
