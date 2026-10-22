# -*- coding: utf-8 -*-
"""
E2E tests for QSVEncC --tune parameter support.

These tests verify that the --tune flag is correctly wired through to
the generated commands and produces valid output when running on
hardware with Intel QSV support.

Run locally:
    uv run pytest tests/e2e/test_e2e_qsvencc_tune.py -v
    SKIP_INTEL=1 uv run pytest tests/e2e -v  # skip Intel tests

Skipped on CI (GitHub Actions sets CI=true).
"""

import pytest

from fastflix.models.encode import QSVEncCAV1Settings, QSVEncCH264Settings, QSVEncCSettings

from tests.e2e.conftest import (
    ON_CI,
    QSVENCC,
    SKIP_INTEL,
    FFMPEG,
    FFPROBE,
    SOURCES,
    create_fastflix,
    run_commands,
    verify_output,
)

pytestmark = [pytest.mark.e2e]

if ON_CI:
    pytestmark.append(pytest.mark.skip(reason="E2E tests skipped on CI"))
if not FFMPEG or not FFPROBE:
    pytestmark.append(pytest.mark.skip(reason="ffmpeg/ffprobe not found"))


TUNE_VALUES = ["hq", "ll", "ull", "lossless"]


def _skip_if_no_qsvencc():
    if not QSVENCC:
        pytest.skip("QSVEncC not found")
    if SKIP_INTEL:
        pytest.skip("Intel tests skipped via SKIP_INTEL")


# ===========================================================================
# Test 1: QSVEncC HEVC --tune flag in generated commands
# ===========================================================================
@pytest.mark.parametrize("tune_value", TUNE_VALUES)
def test_qsvencc_hevc_tune_command(tune_value, tmp_path):
    """QSVEncC HEVC encoder includes --tune flag with correct value in generated command."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"hevc_tune_{tune_value}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCSettings(preset="fastest", bitrate="1000k", tune=tune_value),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_hevc import command_builder

    commands = command_builder.build(fastflix)
    assert commands, "QSVEncC HEVC returned no commands"

    cmd = commands[0].command
    assert "--tune" in cmd, f"--tune not found in command: {cmd}"
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == tune_value, f"Expected tune={tune_value}, got {cmd[tune_idx + 1]}"


# ===========================================================================
# Test 2: QSVEncC AV1 --tune flag in generated commands
# ===========================================================================
@pytest.mark.parametrize("tune_value", TUNE_VALUES)
def test_qsvencc_av1_tune_command(tune_value, tmp_path):
    """QSVEncC AV1 encoder includes --tune flag with correct value in generated command."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"av1_tune_{tune_value}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCAV1Settings(preset="fastest", bitrate="1000k", tune=tune_value),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_av1 import command_builder

    commands = command_builder.build(fastflix)
    assert commands, "QSVEncC AV1 returned no commands"

    cmd = commands[0].command
    assert "--tune" in cmd, f"--tune not found in command: {cmd}"
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == tune_value, f"Expected tune={tune_value}, got {cmd[tune_idx + 1]}"


# ===========================================================================
# Test 3: QSVEncC AVC --tune flag in generated commands
# ===========================================================================
@pytest.mark.parametrize("tune_value", TUNE_VALUES)
def test_qsvencc_avc_tune_command(tune_value, tmp_path):
    """QSVEncC AVC encoder includes --tune flag with correct value in generated command."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"avc_tune_{tune_value}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCH264Settings(preset="fastest", bitrate="1000k", tune=tune_value),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_avc import command_builder

    commands = command_builder.build(fastflix)
    assert commands, "QSVEncC AVC returned no commands"

    cmd = commands[0].command
    assert "--tune" in cmd, f"--tune not found in command: {cmd}"
    tune_idx = cmd.index("--tune")
    assert cmd[tune_idx + 1] == tune_value, f"Expected tune={tune_value}, got {cmd[tune_idx + 1]}"


# ===========================================================================
# Test 4: QSVEncC --tune omitted when not set
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,settings_cls,codec",
    [
        ("qsvencc_hevc", QSVEncCSettings, "hevc"),
        ("qsvencc_av1", QSVEncCAV1Settings, "av1"),
        ("qsvencc_avc", QSVEncCH264Settings, "h264"),
    ],
)
def test_qsvencc_tune_omitted_when_none(encoder_id, settings_cls, codec, tmp_path):
    """--tune is NOT in the command when tune is None (default)."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"{encoder_id}_no_tune.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings_cls(preset="fastest", bitrate="1000k"),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    cmd = commands[0].command
    assert "--tune" not in cmd, f"--tune should not be present when tune is None: {cmd}"


# ===========================================================================
# Test 5: Full encode with --tune hq (HEVC)
# ===========================================================================
def test_qsvencc_hevc_tune_encode(tmp_path):
    """QSVEncC HEVC with --tune hq produces valid output."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / "hevc_tune_encode.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCSettings(preset="fastest", bitrate="1000k", tune="hq"),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_hevc import command_builder

    commands = command_builder.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    verify_output(output_path, "hevc")


# ===========================================================================
# Test 6: Full encode with --tune ll (AV1)
# ===========================================================================
def test_qsvencc_av1_tune_encode(tmp_path):
    """QSVEncC AV1 with --tune ll produces valid output."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / "av1_tune_encode.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCAV1Settings(preset="fastest", bitrate="1000k", tune="ll"),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_av1 import command_builder

    commands = command_builder.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    verify_output(output_path, "av1")


# ===========================================================================
# Test 7: Full encode with --tune hq (AVC)
# ===========================================================================
def test_qsvencc_avc_tune_encode(tmp_path):
    """QSVEncC AVC with --tune hq produces valid output."""
    _skip_if_no_qsvencc()

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / "avc_tune_encode.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=QSVEncCH264Settings(preset="fastest", bitrate="1000k", tune="hq"),
        output_path=output_path,
        work_path=work_path,
        is_rigaya=True,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.qsvencc_avc import command_builder

    commands = command_builder.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    verify_output(output_path, "h264")
