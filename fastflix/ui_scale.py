# -*- coding: utf-8 -*-
"""
UI Scaling module for FastFlix.

Provides a singleton UIScaler that manages scale factors for the entire application.
Scale factors are computed based on the current window size relative to the base
reference size of 1200x680.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from PySide6 import QtCore

BASE_WIDTH = 1200
BASE_HEIGHT = 680


@dataclass
class ScaleFactors:
    """Scale factors for UI elements - immutable, use copy.replace() to modify."""

    width: float = 1.0
    height: float = 1.0
    uniform: float = 1.0
    font: float = 1.0
    icon: float = 1.0


class UIScaler:
    """Singleton for managing UI scaling throughout the application."""

    _instance: UIScaler | None = None

    def __new__(cls) -> UIScaler:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.factors = ScaleFactors()
        self._listeners: list[Callable[[ScaleFactors], None]] = []

    def calculate_factors(self, width: int, height: int) -> None:
        """Calculate and update scale factors based on current window dimensions."""
        width_factor = width / BASE_WIDTH
        height_factor = height / BASE_HEIGHT
        uniform = min(width_factor, height_factor)

        # Use Python 3.13 copy.replace() for immutable update
        self.factors = copy.replace(
            self.factors,
            width=width_factor,
            height=height_factor,
            uniform=uniform,
            font=uniform,
            icon=uniform,
        )
        self._notify_listeners()

    def scale(self, base_value: int) -> int:
        """Scale a base value by the uniform scale factor."""
        return max(1, int(base_value * self.factors.uniform))

    def scale_font(self, base_size: int) -> int:
        """Scale a font size, with minimum of 8px for readability."""
        return max(8, int(base_size * self.factors.font))

    def scale_icon(self, base_size: int) -> int:
        """Scale an icon size, with minimum of 10px for visibility."""
        return max(10, int(base_size * self.factors.icon))

    def scale_size(self, width: int, height: int) -> QtCore.QSize:
        """Scale a width/height pair and return as QSize."""
        return QtCore.QSize(self.scale(width), self.scale(height))

    def add_listener(self, callback: Callable[[ScaleFactors], None]) -> None:
        """Register a callback to be notified when scale factors change."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[ScaleFactors], None]) -> None:
        """Unregister a previously registered callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners of scale factor changes."""
        for callback in self._listeners:
            callback(self.factors)


# Global singleton instance
scaler = UIScaler()
