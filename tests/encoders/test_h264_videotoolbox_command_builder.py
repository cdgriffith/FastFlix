# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.h264_videotoolbox.command_builder import build
from fastflix.encoders.common.helpers import null
from fastflix.models.encode import H264VideoToolboxSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _make_fastflix(encoder_settings, video_settings=None):
    """Create a FastFlix instance for H264 VideoToolbox testing."""
    return create_fastflix_instance(encoder_settings=encoder_settings, video_settings=video_settings)


# ---------------------------------------------------------------------------
# Profile mapping — the fix for #741
# ---------------------------------------------------------------------------
def test_profile_auto_omitted():
    """Profile 'Auto' (index 0) must NOT emit -profile:v — FFmpeg has no H264 profile 0."""
    fastflix = _make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=0, q=50))
    cmd = build(fastflix)[0].command

    assert "-profile:v" not in cmd


def test_profile_baseline():
    """Profile index 1 → -profile:v baseline."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=1, q=50)))[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "baseline"


def test_profile_main():
    """Profile index 2 → -profile:v main."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=2, q=50)))[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "main"


def test_profile_high():
    """Profile index 3 → -profile:v high."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=3, q=50)))[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "high"


def test_profile_extended():
    """Profile index 4 → -profile:v extended."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=4, q=50)))[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "extended"


def test_profile_unknown_index_omitted():
    """An index outside the known map (e.g. 99) should NOT emit -profile:v."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(profile=99, q=50)))[0].command

    assert "-profile:v" not in cmd


# ---------------------------------------------------------------------------
# Quality (constant-Q) mode
# ---------------------------------------------------------------------------
def test_quality_mode_single_pass():
    """Constant quality mode produces exactly one Command."""
    result = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=35, bitrate=None)))

    assert len(result) == 1
    assert result[0].name == "Single pass constant quality"


def test_quality_mode_q_value():
    """-q:v must carry the stringified quality value."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=80, bitrate=None)))[0].command

    idx = cmd.index("-q:v")
    assert cmd[idx + 1] == "80"


def test_quality_mode_boundary_low():
    """Quality value 1 (lowest = best quality) is accepted."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=1, bitrate=None)))[0].command

    idx = cmd.index("-q:v")
    assert cmd[idx + 1] == "1"


def test_quality_mode_boundary_high():
    """Quality value 100 (highest = worst quality) is accepted."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=100, bitrate=None)))[0].command

    idx = cmd.index("-q:v")
    assert cmd[idx + 1] == "100"


def test_quality_mode_no_bitrate_flags():
    """Constant-Q must NOT contain -b:v or -pass flags."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50, bitrate=None)))[0].command

    assert "-b:v" not in cmd
    assert "-pass" not in cmd


# ---------------------------------------------------------------------------
# Bitrate (two-pass) mode
# ---------------------------------------------------------------------------
def test_bitrate_mode_two_passes():
    """Bitrate mode must produce exactly two Commands."""
    result = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=None, bitrate="4000k")))

    assert len(result) == 2
    assert "First pass" in result[0].name
    assert "Second pass" in result[1].name


def test_bitrate_mode_pass_flags():
    """Each pass carries correct -pass value."""
    result = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=None, bitrate="4000k")))

    cmd1 = result[0].command
    assert cmd1[cmd1.index("-pass") + 1] == "1"
    cmd2 = result[1].command
    assert cmd2[cmd2.index("-pass") + 1] == "2"


def test_bitrate_mode_bitrate_value():
    """-b:v must carry the exact bitrate string in both passes."""
    result = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=None, bitrate="1800k")))

    for cmd_obj in result:
        cmd = cmd_obj.command
        idx = cmd.index("-b:v")
        assert cmd[idx + 1] == "1800k"


def test_bitrate_mode_first_pass_null():
    """First pass sends output to null device and skips audio."""
    cmd1 = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=None, bitrate="4000k")))[0].command

    assert null in cmd1
    assert "-an" in cmd1


def test_bitrate_mode_passlogfile_shared():
    """Both passes must reference the same -passlogfile path."""
    with mock.patch("fastflix.encoders.h264_videotoolbox.command_builder.secrets.token_hex", return_value="cafe0123"):
        result = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=None, bitrate="4000k")))

    log1 = result[0].command[result[0].command.index("-passlogfile") + 1]
    log2 = result[1].command[result[1].command.index("-passlogfile") + 1]
    assert log1 == log2
    assert "cafe0123" in log1


# ---------------------------------------------------------------------------
# Boolean options
# ---------------------------------------------------------------------------
def test_booleans_all_false():
    """Default booleans must emit 'false'."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50)))[0].command

    for flag in ("-allow_sw", "-require_sw", "-realtime", "-frames_before", "-frames_after"):
        idx = cmd.index(flag)
        assert cmd[idx + 1] == "false", f"{flag} should be 'false'"


def test_booleans_all_true():
    """All booleans True must emit 'true'."""
    cmd = build(
        _make_fastflix(
            encoder_settings=H264VideoToolboxSettings(
                q=50, allow_sw=True, require_sw=True, realtime=True, frames_before=True, frames_after=True
            )
        )
    )[0].command

    for flag in ("-allow_sw", "-require_sw", "-realtime", "-frames_before", "-frames_after"):
        idx = cmd.index(flag)
        assert cmd[idx + 1] == "true", f"{flag} should be 'true'"


# ---------------------------------------------------------------------------
# Extra / custom FFmpeg options
# ---------------------------------------------------------------------------
def test_extra_options_quality():
    """Custom extra options are appended in quality mode."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50, extra="-tag:v avc1")))[0].command

    assert "-tag:v" in cmd
    assert "avc1" in cmd


def test_extra_both_passes_bitrate():
    """Extra appears in BOTH passes when extra_both_passes is True."""
    result = build(
        _make_fastflix(
            encoder_settings=H264VideoToolboxSettings(
                q=None, bitrate="4000k", extra="-tag:v avc1", extra_both_passes=True
            )
        )
    )

    assert "-tag:v" in result[0].command
    assert "-tag:v" in result[1].command


def test_extra_only_second_pass_by_default():
    """Without extra_both_passes, first pass must NOT have extra options."""
    result = build(
        _make_fastflix(
            encoder_settings=H264VideoToolboxSettings(
                q=None, bitrate="4000k", extra="-tag:v avc1", extra_both_passes=False
            )
        )
    )

    assert "-tag:v" not in result[0].command
    assert "-tag:v" in result[1].command


# ---------------------------------------------------------------------------
# Encoder identification
# ---------------------------------------------------------------------------
def test_encoder_name():
    """Command must contain h264_videotoolbox as the encoder."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50)))[0].command

    assert "h264_videotoolbox" in cmd


def test_command_exe():
    """All commands must declare exe='ffmpeg'."""
    for cmd_obj in build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50))):
        assert cmd_obj.exe == "ffmpeg"


# ---------------------------------------------------------------------------
# Pixel format
# ---------------------------------------------------------------------------
def test_default_pix_fmt():
    """H264 VideoToolbox defaults to yuv420p (8-bit)."""
    assert H264VideoToolboxSettings().pix_fmt == "yuv420p"


def test_pix_fmt_in_command():
    """The pix_fmt must appear in the generated command."""
    cmd = build(_make_fastflix(encoder_settings=H264VideoToolboxSettings(q=50, pix_fmt="yuv420p")))[0].command

    idx = cmd.index("-pix_fmt")
    assert cmd[idx + 1] == "yuv420p"


# ---------------------------------------------------------------------------
# Start/end time
# ---------------------------------------------------------------------------
def test_start_end_time():
    """Start and end times must be stringified in the command."""
    fastflix = _make_fastflix(
        encoder_settings=H264VideoToolboxSettings(q=50),
        video_settings=VideoSettings(start_time=2.5, end_time=15.0, remove_hdr=False, maxrate=None, bufsize=None),
    )
    cmd = build(fastflix)[0].command

    assert "-ss" in cmd
    assert "2.5" in cmd
    assert "-to" in cmd
    assert "15.0" in cmd


# ---------------------------------------------------------------------------
# All-strings regression guard
# ---------------------------------------------------------------------------
def test_all_elements_are_strings_quality():
    """Every element in quality-mode command must be a string."""
    fastflix = _make_fastflix(
        encoder_settings=H264VideoToolboxSettings(profile=3, q=50, allow_sw=True),
        video_settings=VideoSettings(
            start_time=5.0, end_time=30.0, remove_hdr=False, maxrate=8000, bufsize=16000, video_title="Test"
        ),
    )
    for i, el in enumerate(build(fastflix)[0].command):
        assert isinstance(el, str), f"Element at index {i} is {type(el).__name__}: {el!r}"


def test_all_elements_are_strings_bitrate():
    """Every element in both bitrate-mode commands must be a string."""
    fastflix = _make_fastflix(
        encoder_settings=H264VideoToolboxSettings(profile=2, q=None, bitrate="4000k"),
        video_settings=VideoSettings(start_time=1.0, end_time=10.0, remove_hdr=False, maxrate=None, bufsize=None),
    )
    for cmd_obj in build(fastflix):
        for i, el in enumerate(cmd_obj.command):
            assert isinstance(el, str), f"Element at index {i} is {type(el).__name__}: {el!r}"


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------
def test_settings_defaults():
    """Verify sensible defaults on the model."""
    s = H264VideoToolboxSettings()
    assert s.profile == 0
    assert s.q == 50
    assert s.bitrate is None
    assert s.pix_fmt == "yuv420p"
    assert s.allow_sw is False
    assert s.require_sw is False
    assert s.realtime is False
    assert s.frames_before is False
    assert s.frames_after is False


# ---------------------------------------------------------------------------
# Import correctness (regression for wrong import)
# ---------------------------------------------------------------------------
def test_uses_correct_settings_type():
    """h264_videotoolbox must import H264VideoToolboxSettings, not HEVCVideoToolboxSettings."""
    import fastflix.encoders.h264_videotoolbox.command_builder as mod

    # The module should reference H264VideoToolboxSettings
    assert hasattr(mod, "H264VideoToolboxSettings")
    assert not hasattr(mod, "HEVCVideoToolboxSettings")
