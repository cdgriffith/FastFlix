# -*- coding: utf-8 -*-
"""
E2E tests for VideoToolbox (Apple) encoders — HEVC and H264.

These tests verify that commands are correctly generated and, on macOS
hardware with VideoToolbox support, produce valid output files.

Run locally (macOS only):
    uv run pytest tests/e2e/test_e2e_videotoolbox.py -v
    SKIP_MAC=1 uv run pytest tests/e2e -v  # skip Mac tests

Skipped on CI (GitHub Actions sets CI=true).
Skipped on non-Mac platforms (VideoToolbox is macOS-only).
"""

import pytest

from fastflix.models.encode import H264VideoToolboxSettings, HEVCVideoToolboxSettings

from tests.e2e.conftest import (
    FFMPEG,
    FFPROBE,
    ON_CI,
    SKIP_MAC,
    SOURCES,
    create_fastflix,
    has_ffmpeg_encoder,
    run_commands,
    verify_output,
)

pytestmark = [pytest.mark.e2e]

if ON_CI:
    pytestmark.append(pytest.mark.skip(reason="E2E tests skipped on CI"))
if not FFMPEG or not FFPROBE:
    pytestmark.append(pytest.mark.skip(reason="ffmpeg/ffprobe not found"))


def _skip_if_no_videotoolbox(encoder_name: str):
    if not has_ffmpeg_encoder(encoder_name):
        pytest.skip(f"{encoder_name} not available in this FFmpeg build")
    if SKIP_MAC:
        pytest.skip("Mac tests skipped via SKIP_MAC")


# ===========================================================================
# HEVC VideoToolbox
# ===========================================================================


class TestHEVCVideoToolbox:
    """HEVC VideoToolbox encoder E2E tests."""

    def _skip(self):
        _skip_if_no_videotoolbox("hevc_videotoolbox")

    # -- Command generation (no hardware needed, just needs FFmpeg awareness) --

    def test_command_profile_auto(self, tmp_path):
        """Profile Auto omits -profile:v from generated command."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_auto.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=0, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert commands
        cmd = commands[0].command
        assert "-profile:v" not in cmd
        assert "hevc_videotoolbox" in cmd

    def test_command_profile_main(self, tmp_path):
        """Profile Main emits -profile:v main."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_main.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=1, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        cmd = commands[0].command
        idx = cmd.index("-profile:v")
        assert cmd[idx + 1] == "main"

    def test_command_profile_main10(self, tmp_path):
        """Profile Main10 emits -profile:v main10."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_main10.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=2, q=50, pix_fmt="p010le"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        cmd = commands[0].command
        idx = cmd.index("-profile:v")
        assert cmd[idx + 1] == "main10"

    def test_command_bitrate_two_pass(self, tmp_path):
        """Bitrate mode produces two-pass commands."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_bitrate.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="3000k"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert len(commands) == 2
        assert "-pass" in commands[0].command
        assert "-pass" in commands[1].command
        assert "-b:v" in commands[0].command
        assert "-b:v" in commands[1].command

    def test_command_boolean_flags(self, tmp_path):
        """Boolean options (allow_sw, realtime, etc.) appear as 'true'/'false'."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_bools.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(q=50, allow_sw=True, realtime=True),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        cmd = command_builder.build(fastflix)[0].command
        assert cmd[cmd.index("-allow_sw") + 1] == "true"
        assert cmd[cmd.index("-realtime") + 1] == "true"
        assert cmd[cmd.index("-require_sw") + 1] == "false"

    # -- Full encode (needs VideoToolbox hardware) --

    def test_encode_quality_auto_profile(self, tmp_path):
        """Encode with Auto profile and constant quality produces valid HEVC output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_encode_auto.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=0, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")

    def test_encode_quality_main_profile(self, tmp_path):
        """Encode with Main profile and constant quality."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_encode_main.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=1, q=50, pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")

    def test_encode_quality_main10_profile(self, tmp_path):
        """Encode with Main10 profile (10-bit) and constant quality."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_encode_main10.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(profile=2, q=50, pix_fmt="p010le"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")

    def test_encode_bitrate_mode(self, tmp_path):
        """Two-pass bitrate encode produces valid HEVC output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_encode_bitrate.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="3000k"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert len(commands) == 2
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")

    def test_encode_allow_sw(self, tmp_path):
        """Encode with allow_sw=True (software fallback) produces valid output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_allow_sw.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(q=50, allow_sw=True),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")

    def test_encode_mkv_output(self, tmp_path):
        """HEVC VideoToolbox can encode to MKV container."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "hevc_vtb_encode.mkv"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=HEVCVideoToolboxSettings(q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.hevc_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "hevc")


# ===========================================================================
# H264 VideoToolbox
# ===========================================================================


class TestH264VideoToolbox:
    """H264 VideoToolbox encoder E2E tests."""

    def _skip(self):
        _skip_if_no_videotoolbox("h264_videotoolbox")

    # -- Command generation --

    def test_command_profile_auto(self, tmp_path):
        """Profile Auto omits -profile:v from generated command."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_auto.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(profile=0, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert commands
        cmd = commands[0].command
        assert "-profile:v" not in cmd
        assert "h264_videotoolbox" in cmd

    def test_command_profile_baseline(self, tmp_path):
        """Profile baseline emits -profile:v baseline."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_baseline.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(profile=1, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        cmd = command_builder.build(fastflix)[0].command
        idx = cmd.index("-profile:v")
        assert cmd[idx + 1] == "baseline"

    def test_command_profile_high(self, tmp_path):
        """Profile high emits -profile:v high."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_high.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(profile=3, q=50),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        cmd = command_builder.build(fastflix)[0].command
        idx = cmd.index("-profile:v")
        assert cmd[idx + 1] == "high"

    def test_command_bitrate_two_pass(self, tmp_path):
        """Bitrate mode produces two-pass commands."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_bitrate.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(q=None, bitrate="3000k"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert len(commands) == 2

    # -- Full encode --

    def test_encode_quality_auto_profile(self, tmp_path):
        """Encode with Auto profile produces valid H264 output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_encode_auto.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(profile=0, q=50, pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "h264")

    def test_encode_quality_high_profile(self, tmp_path):
        """Encode with High profile produces valid H264 output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_encode_high.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(profile=3, q=50, pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "h264")

    def test_encode_bitrate_mode(self, tmp_path):
        """Two-pass bitrate encode produces valid H264 output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_encode_bitrate.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(q=None, bitrate="3000k", pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        assert len(commands) == 2
        run_commands(commands, work_path)
        verify_output(output_path, "h264")

    def test_encode_allow_sw(self, tmp_path):
        """Encode with allow_sw=True produces valid output."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_allow_sw.mp4"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(q=50, allow_sw=True, pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "h264")

    def test_encode_mkv_output(self, tmp_path):
        """H264 VideoToolbox can encode to MKV container."""
        self._skip()
        source = SOURCES["hdr10plus"]
        if not source.exists():
            pytest.skip("HDR10+ test source not found")

        output_path = tmp_path / "h264_vtb_encode.mkv"
        work_path = tmp_path / "work"
        work_path.mkdir()

        fastflix = create_fastflix(
            source_path=source,
            encoder_settings=H264VideoToolboxSettings(q=50, pix_fmt="yuv420p"),
            output_path=output_path,
            work_path=work_path,
            include_data=False,
            include_attachments=False,
        )

        from fastflix.encoders.h264_videotoolbox import command_builder

        commands = command_builder.build(fastflix)
        run_commands(commands, work_path)
        verify_output(output_path, "h264")
