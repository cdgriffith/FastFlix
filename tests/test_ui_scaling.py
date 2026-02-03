# -*- coding: utf-8 -*-
"""
Tests for the UI scaling system.

These tests verify that the UIScaler singleton correctly calculates scale factors
and that the scaling functions return expected values.
"""

import copy
import pytest
from unittest.mock import MagicMock

from PySide6 import QtCore


class TestUIScaler:
    """Tests for the UIScaler singleton class."""

    def test_singleton(self):
        """Verify UIScaler is a singleton."""
        from fastflix.ui_scale import UIScaler

        scaler1 = UIScaler()
        scaler2 = UIScaler()
        assert scaler1 is scaler2

    def test_calculate_factors_at_base_size(self):
        """Scale factors should be 1.0 at base size (1200x680)."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        scaler.calculate_factors(BASE_WIDTH, BASE_HEIGHT)
        assert scaler.factors.uniform == 1.0
        assert scaler.factors.width == 1.0
        assert scaler.factors.height == 1.0
        assert scaler.factors.font == 1.0
        assert scaler.factors.icon == 1.0

    def test_calculate_factors_scaled_up(self):
        """Scale factors should increase when window is larger than base."""
        from fastflix.ui_scale import UIScaler

        scaler = UIScaler()
        scaler.calculate_factors(2400, 1360)  # 2x base
        assert scaler.factors.uniform == 2.0
        assert scaler.factors.width == 2.0
        assert scaler.factors.height == 2.0

    def test_calculate_factors_scaled_down(self):
        """Scale factors should decrease when window is smaller than base."""
        from fastflix.ui_scale import UIScaler

        scaler = UIScaler()
        scaler.calculate_factors(600, 340)  # 0.5x base
        assert scaler.factors.uniform == 0.5
        assert scaler.factors.width == 0.5
        assert scaler.factors.height == 0.5

    def test_calculate_factors_non_uniform(self):
        """Uniform factor should be the minimum of width and height factors."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        # 2x width, 1x height - uniform should be 1.0
        scaler.calculate_factors(BASE_WIDTH * 2, BASE_HEIGHT)
        assert scaler.factors.width == 2.0
        assert scaler.factors.height == 1.0
        assert scaler.factors.uniform == 1.0

    def test_scale_returns_int(self):
        """scale() should always return an integer."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        scaler.calculate_factors(BASE_WIDTH, BASE_HEIGHT)
        result = scaler.scale(100)
        assert isinstance(result, int)

    def test_scale_minimum_value(self):
        """scale() should never return less than 1."""
        from fastflix.ui_scale import UIScaler

        scaler = UIScaler()
        scaler.calculate_factors(1, 1)  # Very small
        result = scaler.scale(10)
        assert result >= 1

    def test_scale_font_minimum(self):
        """scale_font() should never return less than 8 for readability."""
        from fastflix.ui_scale import UIScaler

        scaler = UIScaler()
        scaler.calculate_factors(1, 1)  # Very small
        result = scaler.scale_font(12)
        assert result >= 8

    def test_scale_icon_minimum(self):
        """scale_icon() should never return less than 10 for visibility."""
        from fastflix.ui_scale import UIScaler

        scaler = UIScaler()
        scaler.calculate_factors(1, 1)  # Very small
        result = scaler.scale_icon(20)
        assert result >= 10

    def test_listener_notification(self):
        """Listeners should be notified when scale factors change."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        callback = MagicMock()
        scaler.add_listener(callback)
        scaler.calculate_factors(BASE_WIDTH, BASE_HEIGHT)
        callback.assert_called_once()
        scaler.remove_listener(callback)

    def test_listener_removal(self):
        """Removed listeners should not be notified."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        callback = MagicMock()
        scaler.add_listener(callback)
        scaler.remove_listener(callback)
        scaler.calculate_factors(BASE_WIDTH, BASE_HEIGHT)
        callback.assert_not_called()

    def test_scale_size_returns_qsize(self):
        """scale_size() should return a QSize object."""
        from fastflix.ui_scale import UIScaler, BASE_WIDTH, BASE_HEIGHT

        scaler = UIScaler()
        scaler.calculate_factors(BASE_WIDTH, BASE_HEIGHT)
        result = scaler.scale_size(100, 50)
        assert isinstance(result, QtCore.QSize)
        assert result.width() == 100
        assert result.height() == 50


class TestScaleFactors:
    """Tests for the ScaleFactors dataclass."""

    def test_default_values(self):
        """ScaleFactors should have default values of 1.0."""
        from fastflix.ui_scale import ScaleFactors

        factors = ScaleFactors()
        assert factors.width == 1.0
        assert factors.height == 1.0
        assert factors.uniform == 1.0
        assert factors.font == 1.0
        assert factors.icon == 1.0

    def test_immutable_with_copy_replace(self):
        """ScaleFactors should support copy.replace() for immutable updates."""
        from fastflix.ui_scale import ScaleFactors

        factors = ScaleFactors()
        new_factors = copy.replace(factors, width=2.0)
        assert factors.width == 1.0  # Original unchanged
        assert new_factors.width == 2.0


class TestUIConstants:
    """Tests for UI constants."""

    def test_base_widths_frozen(self):
        """BaseWidths should be frozen (immutable)."""
        from fastflix.ui_constants import WIDTHS

        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            WIDTHS.MENUBAR = 500

    def test_base_heights_frozen(self):
        """BaseHeights should be frozen (immutable)."""
        from fastflix.ui_constants import HEIGHTS

        with pytest.raises(Exception):
            HEIGHTS.TOP_BAR_BUTTON = 100

    def test_base_icon_sizes_frozen(self):
        """BaseIconSizes should be frozen (immutable)."""
        from fastflix.ui_constants import ICONS

        with pytest.raises(Exception):
            ICONS.SMALL = 50

    def test_constants_have_positive_values(self):
        """All constants should have positive values."""
        from fastflix.ui_constants import WIDTHS, HEIGHTS, ICONS

        for attr in dir(WIDTHS):
            if not attr.startswith("_"):
                assert getattr(WIDTHS, attr) > 0

        for attr in dir(HEIGHTS):
            if not attr.startswith("_"):
                assert getattr(HEIGHTS, attr) > 0

        for attr in dir(ICONS):
            if not attr.startswith("_"):
                assert getattr(ICONS, attr) > 0


class TestUIStyles:
    """Tests for UI style generation."""

    def test_get_scaled_stylesheet_returns_string(self):
        """get_scaled_stylesheet should return a string."""
        from fastflix.ui_styles import get_scaled_stylesheet

        result = get_scaled_stylesheet("onyx")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_scaled_stylesheet_contains_font_size(self):
        """Stylesheet should contain font-size specification."""
        from fastflix.ui_styles import get_scaled_stylesheet

        result = get_scaled_stylesheet("onyx")
        assert "font-size" in result

    def test_get_scaled_stylesheet_onyx_theme(self):
        """Onyx theme should have specific styling."""
        from fastflix.ui_styles import get_scaled_stylesheet

        result = get_scaled_stylesheet("onyx")
        assert "QAbstractItemView" in result
        assert "#4f5962" in result  # Onyx background color

    def test_get_menubar_stylesheet_returns_string(self):
        """get_menubar_stylesheet should return a string."""
        from fastflix.ui_styles import get_menubar_stylesheet

        result = get_menubar_stylesheet()
        assert isinstance(result, str)
        assert "font-size" in result
