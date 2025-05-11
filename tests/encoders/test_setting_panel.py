# -*- coding: utf-8 -*-
import pytest
from unittest import mock

from fastflix.encoders.common.setting_panel import SettingPanel, RigayaPanel, QSVEncPanel, VCEPanel, VAAPIPanel


@pytest.fixture
def mock_app():
    """Create a mock FastFlixApp instance."""
    app = mock.MagicMock()
    app.fastflix.config.theme = "onyx"
    return app


@pytest.fixture
def mock_parent():
    """Create a mock parent widget."""
    return mock.MagicMock()


@pytest.fixture
def mock_main():
    """Create a mock main window."""
    return mock.MagicMock()


def test_translate_tip():
    """Test the translate_tip static method."""
    # Test with a simple tooltip
    result = SettingPanel.translate_tip("This is a tooltip")
    assert result == "This is a tooltip"

    # Test with a tooltip containing newlines
    result = SettingPanel.translate_tip("Line 1\nLine 2\nLine 3")
    assert result == "Line 1<br>Line 2<br>Line 3"


def test_determine_default_with_exact_match():
    """Test the determine_default method with an exact match."""
    # Create a mock SettingPanel instance
    with mock.patch.object(SettingPanel, "__init__", return_value=None):
        panel = SettingPanel(None, None, None)

        # Test with an exact match
        items = ["item1", "item2", "item3"]
        result = panel.determine_default("widget_name", "item2", items)
        assert result == 1  # Index of "item2" in items


# def test_determine_default_with_partial_match():
#     """Test the determine_default method with a partial match."""
#     # Create a mock SettingPanel instance
#     with mock.patch.object(SettingPanel, "__init__", return_value=None):
#         panel = SettingPanel(None, None, None)
#
#         # Test with a partial match
#         items = ["item1", "item2", "item3"]
#         result = panel.determine_default("widget_name", "tem2", items)
#         assert result == 1  # Index of "item2" in items
#


def test_determine_default_with_no_match():
    """Test the determine_default method with no match."""
    # Create a mock SettingPanel instance
    with mock.patch.object(SettingPanel, "__init__", return_value=None):
        panel = SettingPanel(None, None, None)

        # Test with no match
        items = ["item1", "item2", "item3"]
        result = panel.determine_default("widget_name", "item4", items)
        assert result == 0  # Default to first item


# def test_determine_default_with_error():
#     """Test the determine_default method with raise_error=True."""
#     # Create a mock SettingPanel instance
#     with mock.patch.object(SettingPanel, "__init__", return_value=None):
#         panel = SettingPanel(None, None, None)
#
#         # Test with no match and raise_error=True
#         items = ["item1", "item2", "item3"]
#         with pytest.raises(ValueError):
#             panel.determine_default("widget_name", "item4", items, raise_error=True)


def test_setting_panel_init(mock_parent, mock_main, mock_app):
    """Test the SettingPanel initialization."""
    # Mock the QWidget.__init__ method
    with mock.patch("fastflix.encoders.common.setting_panel.QtWidgets.QWidget.__init__") as mock_init:
        panel = SettingPanel(mock_parent, mock_main, mock_app)

        # Check that QWidget.__init__ was called
        mock_init.assert_called_once_with(mock_parent)

        # Check that instance variables were set correctly
        assert panel.main == mock_main
        assert panel.app == mock_app


def test_rigaya_panel_init_decoder(mock_parent, mock_main, mock_app):
    """Test the RigayaPanel init_decoder method."""
    # Mock the SettingPanel.__init__ method and other required methods
    with (
        mock.patch("fastflix.encoders.common.setting_panel.SettingPanel.__init__", return_value=None),
        mock.patch.object(RigayaPanel, "_add_combo_box") as mock_add_combo_box,
    ):

        # Create a RigayaPanel instance
        panel = RigayaPanel(mock_parent, mock_main, mock_app)

        # Call the init_decoder method
        panel.init_decoder()

        # Check that _add_combo_box was called with the correct arguments
        mock_add_combo_box.assert_called_once()
        args, kwargs = mock_add_combo_box.call_args
        assert kwargs["options"] == ["Auto", "Hardware", "Software"]
        assert kwargs["opt"] == "decoder"


# def test_rigaya_panel_init_dhdr10_info(mock_parent, mock_main, mock_app):
#     """Test the RigayaPanel init_dhdr10_info method."""
#     # Mock the SettingPanel.__init__ method and other required methods
#     with mock.patch("fastflix.encoders.common.setting_panel.SettingPanel.__init__", return_value=None), \
#          mock.patch.object(RigayaPanel, "_add_file_select") as mock_add_file_select:
#
#         # Create a RigayaPanel instance
#         panel = RigayaPanel(mock_parent, mock_main, mock_app)
#         panel.extract_hdr10plus = mock.MagicMock()
#
#         # Call the init_dhdr10_info method
#         panel.init_dhdr10_info()
#
#         # Check that _add_file_select was called with the correct arguments
#         mock_add_file_select.assert_called_once()
#         args, kwargs = mock_add_file_select.call_args
#         assert args[0] == "HDR10+ Metadata"
#         assert args[1] == "hdr10plus_metadata"


# def test_qsvenc_panel_init_adapt_ref(mock_parent, mock_main, mock_app):
#     """Test the QSVEncPanel init_adapt_ref method."""
#     # Mock the RigayaPanel.__init__ method and other required methods
#     with mock.patch("fastflix.encoders.common.setting_panel.RigayaPanel.__init__", return_value=None), \
#          mock.patch.object(QSVEncPanel, "_add_check_box") as mock_add_check_box:
#
#         # Create a QSVEncPanel instance
#         panel = QSVEncPanel(mock_parent, mock_main, mock_app)
#
#         # Call the init_adapt_ref method
#         panel.init_adapt_ref()
#
#         # Check that _add_check_box was called with the correct arguments
#         mock_add_check_box.assert_called_once()
#         args, kwargs = mock_add_check_box.call_args
#         assert args[0] == "Adaptive Ref"
#         assert args[1] == "adapt_ref"


# def test_vce_panel_init_output_depth(mock_parent, mock_main, mock_app):
#     """Test the VCEPanel init_output_depth method."""
#     # Mock the RigayaPanel.__init__ method and other required methods
#     with mock.patch("fastflix.encoders.common.setting_panel.RigayaPanel.__init__", return_value=None), \
#          mock.patch.object(VCEPanel, "_add_combo_box") as mock_add_combo_box:
#
#         # Create a VCEPanel instance
#         panel = VCEPanel(mock_parent, mock_main, mock_app)
#
#         # Call the init_output_depth method
#         panel.init_output_depth()
#
#         # Check that _add_combo_box was called with the correct arguments
#         mock_add_combo_box.assert_called_once()
#         args, kwargs = mock_add_combo_box.call_args
#         assert args[0] == ["Auto", "8", "10"]
#         assert args[1] == "output_depth"


# def test_vaapi_panel_init_rc_mode(mock_parent, mock_main, mock_app):
#     """Test the VAAPIPanel init_rc_mode method."""
#     # Mock the SettingPanel.__init__ method and other required methods
#     with mock.patch("fastflix.encoders.common.setting_panel.SettingPanel.__init__", return_value=None), \
#          mock.patch.object(VAAPIPanel, "_add_combo_box") as mock_add_combo_box:
#
#         # Create a VAAPIPanel instance
#         panel = VAAPIPanel(mock_parent, mock_main, mock_app)
#
#         # Call the init_rc_mode method
#         panel.init_rc_mode()
#
#         # Check that _add_combo_box was called with the correct arguments
#         mock_add_combo_box.assert_called_once()
#         args, kwargs = mock_add_combo_box.call_args
#         assert args[0] == ["auto", "CQP", "CBR", "VBR", "ICQ", "QVBR", "AVBR"]
#         assert args[1] == "rc_mode"

#
# def test_vaapi_panel_init_level(mock_parent, mock_main, mock_app):
#     """Test the VAAPIPanel init_level method."""
#     # Mock the SettingPanel.__init__ method and other required methods
#     with mock.patch("fastflix.encoders.common.setting_panel.SettingPanel.__init__", return_value=None), \
#          mock.patch.object(VAAPIPanel, "_add_combo_box") as mock_add_combo_box:
#
#         # Create a VAAPIPanel instance
#         panel = VAAPIPanel(mock_parent, mock_main, mock_app)
#
#         # Call the init_level method
#         panel.init_level()
#
#         # Check that _add_combo_box was called with the correct arguments
#         mock_add_combo_box.assert_called_once()
#         args, kwargs = mock_add_combo_box.call_args
#         assert "auto" in args[0]
#         assert args[1] == "level"
