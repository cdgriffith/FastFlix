# -*- coding: utf-8 -*-
"""
UI Styles module for FastFlix.

Provides scaled stylesheets that adapt to the current UI scale factors.
"""

from fastflix.ui_scale import scaler
from fastflix.ui_constants import FONTS


def get_scaled_stylesheet(theme: str) -> str:
    """Generate a scaled stylesheet based on the current theme and scale factors."""
    font_size = scaler.scale_font(FONTS.LARGE)
    border_radius = scaler.scale(10)

    base = f"QWidget {{ font-size: {font_size}px; }}"

    if theme == "onyx":
        base += f"""
            QAbstractItemView {{ background-color: #4b5054; }}
            QComboBox QAbstractItemView {{ background-color: #1d2023; border: 2px solid #76797c; }}
            QPushButton {{ border-radius: {border_radius}px; }}
            QLineEdit {{
                background-color: #707070;
                color: black;
                border-radius: {border_radius}px;
            }}
            QTextEdit {{ background-color: #707070; color: black; }}
            QTabBar::tab {{ background-color: #4b5054; }}
            QComboBox {{ border-radius: {border_radius}px; }}
            QScrollArea {{ border: 1px solid #919191; }}
        """

    return base


def get_video_options_stylesheet(theme: str) -> str:
    """Generate scaled stylesheet for the video options tab widget."""
    tab_font_size = scaler.scale_font(FONTS.MEDIUM)
    combo_min_height = scaler.scale(22)

    if theme == "onyx":
        return f"""
            * {{ background-color: #4b5054; color: white; }}
            QTabWidget {{ margin-top: {scaler.scale(34)}px; background-color: #4b5054; }}
            QTabBar {{ font-size: {tab_font_size}px; background-color: #4f5962; }}
            QComboBox {{ min-height: {combo_min_height}px; }}
        """
    return ""


def get_menubar_stylesheet() -> str:
    """Generate scaled stylesheet for the menu bar."""
    font_size = scaler.scale_font(FONTS.LARGE)
    return f"font-size: {font_size}px"
