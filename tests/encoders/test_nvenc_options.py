# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from fastflix.encoders.ffmpeg_av1_nvenc.command_builder import build as av1_build
from fastflix.encoders.ffmpeg_hevc_nvenc.command_builder import build as hevc_build
from fastflix.encoders.ffmpeg_hevc_nvenc.settings_panel import presets as hevc_presets
from fastflix.models.encode import FFmpegAV1NVENCSettings, FFmpegNVENCSettings
from fastflix.models.profiles import Profile
from fastflix.models.video import VideoSettings
from tests.conftest import create_fastflix_instance

SUPPORTED_PRESETS = {"slow", "medium", "fast", "p1", "p2", "p3", "p4", "p5", "p6", "p7"}
SUPPORTED_RC = {"constqp", "vbr", "cbr"}


def _cmd(builder, settings, output="out.mkv"):
    vs = VideoSettings(remove_hdr=False, maxrate=None, bufsize=None, output_path=Path(output))
    return builder(create_fastflix_instance(encoder_settings=settings, video_settings=vs))[0].command


def _val(cmd, flag):
    return cmd[cmd.index(flag) + 1]


# ---- presets / legacy migration -------------------------------------------------------------
def test_panel_presets_only_supported():
    assert set(hevc_presets) == SUPPORTED_PRESETS


def test_default_preset_is_supported():
    assert FFmpegNVENCSettings().preset in SUPPORTED_PRESETS
    assert FFmpegAV1NVENCSettings().preset in SUPPORTED_PRESETS


@pytest.mark.parametrize(
    "legacy,preset,tune",
    [
        ("default", "p4", "hq"),
        ("hp", "p1", "hq"),
        ("hq", "p7", "hq"),
        ("bd", "p5", "hq"),
        ("ll", "p4", "ll"),
        ("llhp", "p1", "ll"),
        ("llhq", "p7", "ll"),
        ("lossless", "p4", "lossless"),
        ("losslesshp", "p1", "lossless"),
    ],
)
def test_legacy_presets_migrated(legacy, preset, tune):
    s = FFmpegNVENCSettings(preset=legacy, tune="hq")
    assert s.preset == preset
    assert s.tune == tune


@pytest.mark.parametrize("preset", sorted(SUPPORTED_PRESETS))
def test_supported_presets_untouched(preset):
    s = FFmpegNVENCSettings(preset=preset, tune="uhq")
    assert (s.preset, s.tune) == (preset, "uhq")


@pytest.mark.parametrize(
    "legacy,rc",
    [
        ("vbr_minqp", "vbr"),
        ("vbr_2pass", "vbr"),
        ("vbr_hq", "vbr"),
        ("ll_2pass_quality", "vbr"),
        ("ll_2pass_size", "vbr"),
        ("cbr_hq", "cbr"),
        ("cbr_ld_hq", "cbr"),
    ],
)
def test_legacy_rc_migrated(legacy, rc):
    assert FFmpegNVENCSettings(rc=legacy).rc == rc


@pytest.mark.parametrize("rc", [None, "constqp", "vbr", "cbr"])
def test_valid_rc_untouched(rc):
    assert FFmpegNVENCSettings(rc=rc).rc == rc


def test_legacy_profile_loads_and_builds_valid_command():
    profile = Profile(ffmpeg_hevc_nvenc={"preset": "llhq", "tune": "hq", "rc": "cbr_hq", "bitrate": "5000k"})
    settings = profile.ffmpeg_hevc_nvenc
    cmd = _cmd(hevc_build, settings)
    assert _val(cmd, "-preset:v") == "p7"
    assert _val(cmd, "-tune:v") == "ll"
    assert _val(cmd, "-rc:v") == "cbr"
    assert set(hevc_presets) >= {_val(cmd, "-preset:v")}


def test_builder_never_emits_removed_values():
    for preset in ["hp", "hq", "bd", "ll", "llhq", "llhp", "lossless", "losslesshp"]:
        cmd = _cmd(hevc_build, FFmpegNVENCSettings(preset=preset, bitrate=None, qp=20))
        assert _val(cmd, "-preset:v") in SUPPORTED_PRESETS


# ---- multipass ------------------------------------------------------------------------------
def test_hevc_multipass_default_fullres_bitrate():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(bitrate="6000k"))
    assert _val(cmd, "-multipass:v") == "fullres"


@pytest.mark.parametrize("mode", ["qres", "fullres"])
def test_hevc_multipass_selectable(mode):
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(bitrate="6000k", multipass=mode))
    assert _val(cmd, "-multipass:v") == mode


def test_hevc_multipass_disabled_omitted():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(bitrate="6000k", multipass="disabled"))
    assert "-multipass:v" not in cmd


def test_hevc_multipass_not_in_qp_mode():
    assert "-multipass:v" not in _cmd(hevc_build, FFmpegNVENCSettings(bitrate=None, qp=25))


# ---- defaults are backward compatible ---------------------------------------------------------
NEW_FLAGS = [
    "-temporal-aq:v",
    "-aq-strength:v",
    "-tf_level",
    "-lookahead_level",
    "-split_encode_mode",
    "-weighted_pred",
    "-unidir_b",
    "-no-scenecut",
    "-cq:v",
]


def test_hevc_defaults_emit_no_new_flags():
    for settings in (FFmpegNVENCSettings(), FFmpegNVENCSettings(bitrate=None, qp=25)):
        cmd = _cmd(hevc_build, settings)
        for flag in NEW_FLAGS:
            assert flag not in cmd, flag


def test_av1_defaults_do_not_gain_new_flags():
    cmd = _cmd(av1_build, FFmpegAV1NVENCSettings())
    for flag in ("-tf_level", "-lookahead_level", "-split_encode_mode", "-weighted_pred", "-no-scenecut", "-cq:v"):
        assert flag not in cmd


# ---- new HEVC options -------------------------------------------------------------------------
def test_hevc_temporal_aq():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(temporal_aq=1))
    assert _val(cmd, "-temporal-aq:v") == "1"


def test_hevc_aq_strength_only_when_changed():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(spatial_aq=1, aq_strength=12))
    assert _val(cmd, "-aq-strength:v") == "12"


def test_hevc_tf_level_and_lookahead_level():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(tf_level="4", lookahead_level="auto", rc_lookahead=32))
    assert _val(cmd, "-tf_level") == "4"
    assert _val(cmd, "-lookahead_level") == "auto"


def test_hevc_split_weighted_unidir_scenecut():
    cmd = _cmd(
        hevc_build,
        FFmpegNVENCSettings(split_encode_mode="forced", weighted_pred=1, unidir_b=True, no_scenecut=True),
    )
    assert _val(cmd, "-split_encode_mode") == "forced"
    assert _val(cmd, "-weighted_pred") == "1"
    assert _val(cmd, "-unidir_b") == "1"
    assert _val(cmd, "-no-scenecut") == "1"


def test_hevc_cq_mode():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(bitrate=None, qp=25, cq=24))
    assert _val(cmd, "-cq:v") == "24"
    assert _val(cmd, "-rc:v") == "vbr"
    assert _val(cmd, "-b:v") == "0"
    assert "-qp:v" not in cmd


def test_hevc_cq_ignored_in_bitrate_mode():
    cmd = _cmd(hevc_build, FFmpegNVENCSettings(bitrate="5000k", cq=24))
    assert "-cq:v" not in cmd


# ---- AV1 mirror -------------------------------------------------------------------------------
def test_av1_new_options():
    cmd = _cmd(
        av1_build,
        FFmpegAV1NVENCSettings(
            tf_level="0", lookahead_level="2", split_encode_mode="2", weighted_pred=1, no_scenecut=True
        ),
    )
    assert _val(cmd, "-tf_level") == "0"
    assert _val(cmd, "-lookahead_level") == "2"
    assert _val(cmd, "-split_encode_mode") == "2"
    assert _val(cmd, "-weighted_pred") == "1"
    assert _val(cmd, "-no-scenecut") == "1"


def test_av1_cq_mode():
    cmd = _cmd(av1_build, FFmpegAV1NVENCSettings(bitrate=None, qp=28, cq=30))
    assert _val(cmd, "-cq:v") == "30"
    assert _val(cmd, "-rc:v") == "vbr"
    assert "-qp:v" not in cmd
