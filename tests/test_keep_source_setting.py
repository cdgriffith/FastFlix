# -*- coding: utf-8 -*-
"""
Tests for the keep_source_after_encode setting (#677).

Verifies:
- Config field defaults to False
- Config round-trips through serialization
- add_to_queue() clears video when setting is off (default)
- add_to_queue() keeps video when setting is on
"""

from pathlib import Path
from unittest import mock

import pytest

from fastflix.models.config import Config


@pytest.fixture
def config():
    return Config(
        version="4.0.0",
        ffmpeg=Path("ffmpeg"),
        ffprobe=Path("ffprobe"),
        work_path=Path("work_path"),
    )


class TestConfigField:
    def test_default_is_false(self, config):
        assert config.keep_source_after_encode is False

    def test_can_set_true(self, config):
        config.keep_source_after_encode = True
        assert config.keep_source_after_encode is True

    def test_round_trip_model_dump(self, config):
        config.keep_source_after_encode = True
        data = config.model_dump()
        assert data["keep_source_after_encode"] is True

    def test_round_trip_model_dump_default(self, config):
        data = config.model_dump()
        assert data["keep_source_after_encode"] is False


class TestAddToQueueBehavior:
    """Test that add_to_queue respects the keep_source_after_encode setting."""

    @pytest.fixture
    def mock_main(self, config):
        """Create a mock Main widget with the encoding mixin behavior."""
        main = mock.MagicMock()
        main.app.fastflix.config = config
        main.app.fastflix.current_video = mock.MagicMock()
        main.video_options.queue.add_to_queue.return_value = None
        return main

    def test_clears_video_when_setting_off(self, mock_main):
        """Default behavior: clear source after adding to queue."""
        mock_main.app.fastflix.config.keep_source_after_encode = False

        from fastflix.widgets.main_encoding import EncodingMixin

        mixin = EncodingMixin()
        mixin.__dict__.update(
            {
                "app": mock_main.app,
                "video_options": mock_main.video_options,
                "clear_current_video": mock_main.clear_current_video,
            }
        )
        result = EncodingMixin.add_to_queue(mixin)

        assert result is True
        mock_main.clear_current_video.assert_called_once()

    def test_keeps_video_when_setting_on(self, mock_main):
        """With setting enabled: keep source after adding to queue."""
        mock_main.app.fastflix.config.keep_source_after_encode = True

        from fastflix.widgets.main_encoding import EncodingMixin

        mixin = EncodingMixin()
        mixin.__dict__.update(
            {
                "app": mock_main.app,
                "video_options": mock_main.video_options,
                "clear_current_video": mock_main.clear_current_video,
            }
        )
        result = EncodingMixin.add_to_queue(mixin)

        assert result is True
        mock_main.clear_current_video.assert_not_called()

    def test_no_clear_on_error(self, mock_main):
        """If add_to_queue raises, clear_current_video should not be called."""
        from fastflix.exceptions import FastFlixInternalException
        from fastflix.widgets.main_encoding import EncodingMixin

        mock_main.video_options.queue.add_to_queue.side_effect = FastFlixInternalException("test error")

        mixin = EncodingMixin()
        mixin.__dict__.update(
            {
                "app": mock_main.app,
                "video_options": mock_main.video_options,
                "clear_current_video": mock_main.clear_current_video,
            }
        )

        with mock.patch("fastflix.widgets.main_encoding.error_message"):
            result = EncodingMixin.add_to_queue(mixin)

        assert result is None
        mock_main.clear_current_video.assert_not_called()

    def test_no_clear_when_queue_returns_code(self, mock_main):
        """If queue.add_to_queue returns a non-None code, clear is not reached."""
        from fastflix.widgets.main_encoding import EncodingMixin

        mock_main.video_options.queue.add_to_queue.return_value = False

        mixin = EncodingMixin()
        mixin.__dict__.update(
            {
                "app": mock_main.app,
                "video_options": mock_main.video_options,
                "clear_current_video": mock_main.clear_current_video,
            }
        )
        result = EncodingMixin.add_to_queue(mixin)

        assert result is False
        mock_main.clear_current_video.assert_not_called()
