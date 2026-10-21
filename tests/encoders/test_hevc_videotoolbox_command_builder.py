# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.hevc_videotoolbox.command_builder import build
from fastflix.encoders.common.helpers import null
from fastflix.models.encode import HEVCVideoToolboxSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _make_fastflix(encoder_settings, video_settings=None):
    """Create a FastFlix instance for HEVC VideoToolbox testing."""
    return create_fastflix_instance(encoder_settings=encoder_settings, video_settings=video_settings)


# ---------------------------------------------------------------------------
# Profile mapping
# ---------------------------------------------------------------------------
def test_profile_auto_omitted():
    """Profile 'Auto' (index 0) must NOT emit -profile:v — FFmpeg has no profile 0 for HEVC."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(profile=0, q=50))
    result = build(fastflix)

    cmd = result[0].command
    assert "-profile:v" not in cmd


def test_profile_main():
    """Profile index 1 → -profile:v main."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(profile=1, q=50))
    cmd = build(fastflix)[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "main"


def test_profile_main10():
    """Profile index 2 → -profile:v main10."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(profile=2, q=50))
    cmd = build(fastflix)[0].command

    idx = cmd.index("-profile:v")
    assert cmd[idx + 1] == "main10"


def test_profile_unknown_index_omitted():
    """An index outside the known map (e.g. 99) should NOT emit -profile:v."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(profile=99, q=50))
    cmd = build(fastflix)[0].command

    assert "-profile:v" not in cmd


# ---------------------------------------------------------------------------
# Quality (constant-Q) mode
# ---------------------------------------------------------------------------
def test_quality_mode_single_pass():
    """Constant quality mode produces exactly one Command."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=35, bitrate=None))
    result = build(fastflix)

    assert len(result) == 1
    assert result[0].name == "Single pass constant quality"


def test_quality_mode_q_value():
    """-q:v must carry the stringified quality value."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=15, bitrate=None))
    cmd = build(fastflix)[0].command

    idx = cmd.index("-q:v")
    assert cmd[idx + 1] == "15"


def test_quality_mode_no_bitrate_flags():
    """Constant-Q mode must NOT contain -b:v or -pass flags."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50, bitrate=None))
    cmd = build(fastflix)[0].command

    assert "-b:v" not in cmd
    assert "-pass" not in cmd


# ---------------------------------------------------------------------------
# Bitrate (two-pass) mode
# ---------------------------------------------------------------------------
def test_bitrate_mode_two_passes():
    """Bitrate mode must produce exactly two Commands."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k"))
    result = build(fastflix)

    assert len(result) == 2
    assert "First pass" in result[0].name
    assert "Second pass" in result[1].name


def test_bitrate_mode_pass_flags():
    """Each pass command carries -pass 1 / -pass 2."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k"))
    result = build(fastflix)

    cmd1 = result[0].command
    assert cmd1[cmd1.index("-pass") + 1] == "1"

    cmd2 = result[1].command
    assert cmd2[cmd2.index("-pass") + 1] == "2"


def test_bitrate_mode_bitrate_value():
    """-b:v must carry the exact bitrate string."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="12000k"))
    result = build(fastflix)

    for cmd_obj in result:
        cmd = cmd_obj.command
        idx = cmd.index("-b:v")
        assert cmd[idx + 1] == "12000k"


def test_bitrate_mode_first_pass_null_output():
    """First pass discards output to null device."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k"))
    cmd1 = build(fastflix)[0].command

    assert null in cmd1
    assert "-an" in cmd1  # no audio in first pass


def test_bitrate_mode_second_pass_no_audio_suppression():
    """Second pass must NOT suppress audio (no -an flag)."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k"))
    cmd2 = build(fastflix)[1].command

    assert "-an" not in cmd2


def test_bitrate_mode_passlogfile_shared():
    """Both passes must reference the same -passlogfile path."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k"))

    with mock.patch("fastflix.encoders.hevc_videotoolbox.command_builder.secrets.token_hex", return_value="deadbeef"):
        result = build(fastflix)

    logfile_1 = result[0].command[result[0].command.index("-passlogfile") + 1]
    logfile_2 = result[1].command[result[1].command.index("-passlogfile") + 1]
    assert logfile_1 == logfile_2
    assert "deadbeef" in logfile_1


# ---------------------------------------------------------------------------
# Boolean options
# ---------------------------------------------------------------------------
def test_boolean_options_all_false():
    """Default booleans (False) must emit 'false' strings."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(
            q=50,
            allow_sw=False,
            require_sw=False,
            realtime=False,
            frames_before=False,
            frames_after=False,
        )
    )
    cmd = build(fastflix)[0].command

    for flag in ("-allow_sw", "-require_sw", "-realtime", "-frames_before", "-frames_after"):
        idx = cmd.index(flag)
        assert cmd[idx + 1] == "false", f"{flag} should be 'false'"


def test_boolean_options_all_true():
    """All booleans set to True must emit 'true' strings."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(
            q=50,
            allow_sw=True,
            require_sw=True,
            realtime=True,
            frames_before=True,
            frames_after=True,
        )
    )
    cmd = build(fastflix)[0].command

    for flag in ("-allow_sw", "-require_sw", "-realtime", "-frames_before", "-frames_after"):
        idx = cmd.index(flag)
        assert cmd[idx + 1] == "true", f"{flag} should be 'true'"


def test_boolean_mixed():
    """Verify each boolean flag is independent."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(
            q=50,
            allow_sw=True,
            require_sw=False,
            realtime=True,
            frames_before=False,
            frames_after=True,
        )
    )
    cmd = build(fastflix)[0].command

    assert cmd[cmd.index("-allow_sw") + 1] == "true"
    assert cmd[cmd.index("-require_sw") + 1] == "false"
    assert cmd[cmd.index("-realtime") + 1] == "true"
    assert cmd[cmd.index("-frames_before") + 1] == "false"
    assert cmd[cmd.index("-frames_after") + 1] == "true"


# ---------------------------------------------------------------------------
# Extra / custom FFmpeg options
# ---------------------------------------------------------------------------
def test_extra_options_quality_mode():
    """Custom extra options are appended in quality mode."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50, extra="-tag:v hvc1"))
    cmd = build(fastflix)[0].command

    assert "-tag:v" in cmd
    assert "hvc1" in cmd


def test_extra_options_bitrate_second_pass():
    """Custom extra options appear in second pass of bitrate mode."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k", extra="-tag:v hvc1"))
    result = build(fastflix)

    cmd2 = result[1].command
    assert "-tag:v" in cmd2
    assert "hvc1" in cmd2


def test_extra_both_passes():
    """Extra options appear in BOTH passes when extra_both_passes is True."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k", extra="-tag:v hvc1", extra_both_passes=True)
    )
    result = build(fastflix)

    cmd1 = result[0].command
    cmd2 = result[1].command
    assert "-tag:v" in cmd1
    assert "-tag:v" in cmd2


def test_no_extra_in_first_pass_by_default():
    """Without extra_both_passes, first pass must NOT have extra options."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(q=None, bitrate="6000k", extra="-tag:v hvc1", extra_both_passes=False)
    )
    result = build(fastflix)

    cmd1 = result[0].command
    assert "-tag:v" not in cmd1


def test_empty_extra_no_crash():
    """Empty extra string must not inject empty args."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50, extra=""))
    cmd = build(fastflix)[0].command

    assert "" not in cmd  # no empty-string elements


# ---------------------------------------------------------------------------
# Pixel format
# ---------------------------------------------------------------------------
def test_default_pix_fmt_hevc():
    """HEVC VideoToolbox defaults to p010le (10-bit for HDR)."""
    settings = HEVCVideoToolboxSettings()
    assert settings.pix_fmt == "p010le"


def test_pix_fmt_in_command():
    """The pix_fmt must appear in the generated command via generate_all."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50, pix_fmt="yuv420p"))
    cmd = build(fastflix)[0].command

    assert "-pix_fmt" in cmd
    idx = cmd.index("-pix_fmt")
    assert cmd[idx + 1] == "yuv420p"


# ---------------------------------------------------------------------------
# Encoder identification
# ---------------------------------------------------------------------------
def test_encoder_name_in_command():
    """Command must contain hevc_videotoolbox as the encoder."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50))
    cmd = build(fastflix)[0].command

    assert "hevc_videotoolbox" in cmd


def test_command_exe_is_ffmpeg():
    """All commands must declare exe='ffmpeg'."""
    fastflix = _make_fastflix(encoder_settings=HEVCVideoToolboxSettings(q=50))
    for cmd_obj in build(fastflix):
        assert cmd_obj.exe == "ffmpeg"


# ---------------------------------------------------------------------------
# Start/end time
# ---------------------------------------------------------------------------
def test_start_end_time():
    """Start and end times must be stringified in the command."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(q=50),
        video_settings=VideoSettings(
            start_time=5.5,
            end_time=30.0,
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )
    cmd = build(fastflix)[0].command

    assert "-ss" in cmd
    assert "5.5" in cmd
    assert "-to" in cmd
    assert "30.0" in cmd


# ---------------------------------------------------------------------------
# Color details
# ---------------------------------------------------------------------------
def test_color_details_preserved():
    """Color primaries/transfer/space should be in the command when HDR is not removed."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(q=50),
        video_settings=VideoSettings(
            remove_hdr=False,
            color_primaries="bt2020",
            color_transfer="smpte2084",
            color_space="bt2020nc",
            maxrate=None,
            bufsize=None,
        ),
    )
    cmd = build(fastflix)[0].command

    assert "-color_primaries" in cmd
    assert "bt2020" in cmd
    assert "-color_trc" in cmd
    assert "smpte2084" in cmd
    assert "-colorspace" in cmd
    assert "bt2020nc" in cmd


# ---------------------------------------------------------------------------
# All elements are strings (regression guard)
# ---------------------------------------------------------------------------
def test_all_elements_are_strings_quality():
    """Every element in the quality-mode command must be a string."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(profile=2, q=50, allow_sw=True),
        video_settings=VideoSettings(
            start_time=5.0,
            end_time=30.0,
            remove_hdr=False,
            maxrate=8000,
            bufsize=16000,
            video_title="Test",
        ),
    )
    cmd = build(fastflix)[0].command

    for i, element in enumerate(cmd):
        assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"


def test_all_elements_are_strings_bitrate():
    """Every element in both bitrate-mode commands must be a string."""
    fastflix = _make_fastflix(
        encoder_settings=HEVCVideoToolboxSettings(profile=1, q=None, bitrate="6000k", allow_sw=True),
        video_settings=VideoSettings(
            start_time=1.0,
            end_time=10.0,
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )
    for cmd_obj in build(fastflix):
        for i, element in enumerate(cmd_obj.command):
            assert isinstance(element, str), f"Element at index {i} is {type(element).__name__}: {element!r}"


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------
def test_settings_defaults():
    """Verify sensible defaults on the model."""
    s = HEVCVideoToolboxSettings()
    assert s.profile == 0
    assert s.q == 50
    assert s.bitrate is None
    assert s.pix_fmt == "p010le"
    assert s.allow_sw is False
    assert s.require_sw is False
    assert s.realtime is False
    assert s.frames_before is False
    assert s.frames_after is False
