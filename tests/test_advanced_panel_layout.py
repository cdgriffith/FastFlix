# -*- coding: utf-8 -*-
"""Tests for the Advanced panel QGroupBox layout.

Verifies that the panel renders correctly at realistic sizes,
the scroll area works, and groups don't compress.
"""

import pytest
from unittest import mock
from PySide6 import QtWidgets


@pytest.fixture(scope="session")
def qapp():
    """Create or reuse a QApplication instance for the test session."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def mock_app():
    """Create a mock FastFlixApp with the minimum config needed by AdvancedPanel."""
    app = mock.MagicMock()
    app.fastflix.config.theme = "onyx"
    app.fastflix.config.suppress_video_speed_warning = True
    app.fastflix.config.suppress_reverse_video_warning = True
    app.fastflix.current_video = None
    return app


@pytest.fixture
def mock_parent(qapp):
    """Create a real QWidget parent with a mocked .main attribute."""
    parent = QtWidgets.QWidget()
    parent.main = mock.MagicMock()
    parent.main.page_update = mock.MagicMock()
    parent.main.remove_hdr = False
    return parent


@pytest.fixture
def advanced_panel(mock_parent, mock_app):
    """Create a real AdvancedPanel instance with mocked dependencies."""
    from fastflix.widgets.panels.advanced_panel import AdvancedPanel

    panel = AdvancedPanel(mock_parent, mock_app)
    return panel


# --- Structure tests ---


def test_panel_has_scroll_area(advanced_panel):
    """The panel must contain a QScrollArea as its main child."""
    scroll_areas = advanced_panel.findChildren(QtWidgets.QScrollArea)
    assert len(scroll_areas) == 1, "Panel should have exactly one QScrollArea"


def test_panel_has_five_groups(advanced_panel):
    """The panel must contain exactly 5 QGroupBox sections."""
    groups = advanced_panel.findChildren(QtWidgets.QGroupBox)
    assert len(groups) == 5, f"Expected 5 QGroupBox, found {len(groups)}"
    titles = sorted(g.title() for g in groups)
    assert "Color" in titles
    assert "Frame Rate" in titles
    assert "Output" in titles
    assert "Video Details" in titles
    assert "Video Processing" in titles


def test_all_key_widgets_exist(advanced_panel):
    """All key widget attributes must be present."""
    widgets = [
        "incoming_fps_widget",
        "outgoing_fps_widget",
        "incoming_same_as_source",
        "outgoing_same_as_source",
        "vsync_widget",
        "video_speed_widget",
        "reverse_video_widget",
        "tone_map_widget",
        "brightness_widget",
        "contrast_widget",
        "saturation_widget",
        "gamma_widget",
        "hue_widget",
        "denoise_type_widget",
        "denoise_strength_widget",
        "deblock_widget",
        "deblock_size_widget",
        "color_primaries_widget",
        "color_transfer_widget",
        "color_space_widget",
        "maxrate_widget",
        "bufsize_widget",
        "video_title",
        "video_track_title",
    ]
    for name in widgets:
        assert hasattr(advanced_panel, name), f"Missing widget: {name}"
        assert getattr(advanced_panel, name) is not None, f"Widget is None: {name}"


# --- Grid column stretch tests ---


def test_groups_have_column_stretch(advanced_panel):
    """Each group's grid layout must have column stretch set on all columns."""
    groups = advanced_panel.findChildren(QtWidgets.QGroupBox)
    for group in groups:
        gl = group.layout()
        assert isinstance(gl, QtWidgets.QGridLayout), f"{group.title()} should use QGridLayout"
        col_count = gl.columnCount()
        for col in range(col_count):
            stretch = gl.columnStretch(col)
            assert stretch > 0, f"{group.title()} column {col} has no stretch (stretch={stretch})"


# --- Scroll behavior tests ---


REALISTIC_PANEL_WIDTH = 1500
REALISTIC_PANEL_HEIGHT = 400  # typical tab area height in FastFlix


def test_container_has_minimum_height(advanced_panel):
    """The scroll area's container widget must have a minimum height > the typical viewport."""
    scroll = advanced_panel.findChild(QtWidgets.QScrollArea)
    container = scroll.widget()
    assert container.minimumHeight() >= 500, (
        f"Container minimumHeight ({container.minimumHeight()}) must be >= 500 "
        f"to prevent compression at typical viewport size ({REALISTIC_PANEL_HEIGHT}px)"
    )


def test_scroll_area_scrolls_at_small_size(advanced_panel):
    """When the panel is small, the vertical scrollbar must be available."""
    advanced_panel.resize(REALISTIC_PANEL_WIDTH, REALISTIC_PANEL_HEIGHT)
    advanced_panel.show()
    # Force layout recalculation
    QtWidgets.QApplication.processEvents()

    scroll = advanced_panel.findChild(QtWidgets.QScrollArea)
    vbar = scroll.verticalScrollBar()

    # The scrollbar should have a range > 0 (meaning content overflows viewport)
    assert vbar.maximum() > 0, (
        f"Scroll area should be scrollable at {REALISTIC_PANEL_WIDTH}x{REALISTIC_PANEL_HEIGHT}, "
        f"but scrollbar max is {vbar.maximum()}"
    )
    advanced_panel.hide()


def test_groups_not_compressed_at_small_size(advanced_panel):
    """At small viewport size, groups must maintain usable height (not crushed)."""
    advanced_panel.resize(REALISTIC_PANEL_WIDTH, REALISTIC_PANEL_HEIGHT)
    advanced_panel.show()
    QtWidgets.QApplication.processEvents()

    groups = advanced_panel.findChildren(QtWidgets.QGroupBox)
    min_usable_heights = {
        "Video Details": 50,
        "Frame Rate": 70,
        "Video Processing": 160,
        "Color": 50,
        "Output": 50,
    }
    for group in groups:
        expected_min = min_usable_heights.get(group.title(), 50)
        actual_height = group.height()
        assert actual_height >= expected_min, (
            f"{group.title()} height is {actual_height}px, expected at least {expected_min}px for usability"
        )
    advanced_panel.hide()
