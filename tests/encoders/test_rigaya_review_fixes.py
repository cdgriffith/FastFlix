# -*- coding: utf-8 -*-
"""Regression tests for the NVEncC / QSVEncC / VCEEncC review fixes (checked against rigaya's option docs)."""

import importlib
from pathlib import Path

import pytest
from box import Box

from fastflix.encoders.common.encc_helpers import NVENC_PROFILES, NVENC_TUNES
from fastflix.models import encode as enc
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance

# (encoder module, settings class name, config attribute)
BUILDERS = {
    "nvencc_hevc": ("NVEncCSettings", "nvencc"),
    "nvencc_av1": ("NVEncCAV1Settings", "nvencc"),
    "nvencc_avc": ("NVEncCAVCSettings", "nvencc"),
    "qsvencc_hevc": ("QSVEncCSettings", "qsvencc"),
    "qsvencc_av1": ("QSVEncCAV1Settings", "qsvencc"),
    "qsvencc_avc": ("QSVEncCH264Settings", "qsvencc"),
    "vceencc_hevc": ("VCEEncCSettings", "vceencc"),
    "vceencc_av1": ("VCEEncCAV1Settings", "vceencc"),
    "vceencc_avc": ("VCEEncCAVCSettings", "vceencc"),
}
HDR_BUILDERS = [x for x in BUILDERS if not x.endswith("avc")]


def make(name, video_settings=None, stream_id="0x1", hdr=False, **settings):
    cls_name, config_attr = BUILDERS[name]
    fastflix = create_fastflix_instance(
        encoder_settings=getattr(enc, cls_name)(**settings), video_settings=video_settings, hdr10_metadata=hdr
    )
    fastflix.current_video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "id": stream_id,
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "color_space": "bt2020nc",
                        "color_transfer": "smpte2084",
                        "color_primaries": "bt2020",
                        "chroma_location": "left",
                        "bit_depth": 10,
                        "r_frame_rate": "24000/1001",
                        "avg_frame_rate": "24000/1001",
                        "width": 1920,
                        "height": 1080,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    setattr(fastflix.config, config_attr, Path("EncC64"))
    return fastflix


def build(name, **kwargs):
    module = importlib.import_module(f"fastflix.encoders.{name}.command_builder")
    return module.build(make(name, **kwargs))[0].command


def vs(**kwargs):
    kwargs.setdefault("maxrate", None)
    kwargs.setdefault("bufsize", None)
    kwargs.setdefault("remove_hdr", False)
    return VideoSettings(**kwargs)


def value_after(cmd, flag):
    return cmd[cmd.index(flag) + 1]


# Item 4: HDR10 static metadata must not be written when tone mapping to SDR


@pytest.mark.parametrize("name", HDR_BUILDERS)
def test_hdr_metadata_emitted_when_not_removing_hdr(name):
    cmd = build(name, hdr=True, video_settings=vs())
    assert "--master-display" in cmd
    assert "--max-cll" in cmd


@pytest.mark.parametrize("name", HDR_BUILDERS)
def test_hdr_metadata_not_emitted_when_removing_hdr(name):
    cmd = build(name, hdr=True, video_settings=vs(remove_hdr=True))
    assert "--master-display" not in cmd
    assert "--max-cll" not in cmd
    assert "hdr2sdr=hable" in " ".join(cmd)


# Item 5: custom args are split like a shell, so quoted values stay one argument


@pytest.mark.parametrize("name", list(BUILDERS))
def test_extra_args_respect_quotes(name):
    cmd = build(name, extra='--output-buf 8 --log "C:\\my logs\\enc.log"')
    assert "C:\\my logs\\enc.log" in cmd
    assert "--output-buf" in cmd


# Item 9: video stream id 0 is a real id


@pytest.mark.parametrize("name", list(BUILDERS))
def test_video_streamid_zero_is_emitted(name):
    cmd = build(name, stream_id="0x0")
    assert value_after(cmd, "--video-streamid") == "0"


@pytest.mark.parametrize("name", list(BUILDERS))
def test_video_streamid_nonzero(name):
    cmd = build(name, stream_id="0x1")
    assert value_after(cmd, "--video-streamid") == "1"


def test_split_extra_args_keeps_windows_backslashes(monkeypatch):
    from fastflix.encoders.common import encc_helpers

    monkeypatch.setattr(encc_helpers.sys, "platform", "win32")
    assert encc_helpers.split_extra_args(r"--log C:\logs\enc.log --x 'a b'") == [
        "--log",
        r"C:\logs\enc.log",
        "--x",
        "a b",
    ]


# Item 1: --pa and its parameters are separate argv tokens


@pytest.mark.parametrize("name", ["vceencc_hevc", "vceencc_av1", "vceencc_avc"])
def test_vce_pre_analysis_is_two_tokens(name):
    cmd = build(name, pre_analysis=True)
    assert all(" " not in x for x in cmd if x.startswith("--"))
    assert value_after(cmd, "--pa").startswith("sc=medium,ss=high")


# Item 3: output fps is only available via NVEncC's --vpp-fruc


@pytest.mark.parametrize("name", ["nvencc_hevc", "nvencc_av1", "nvencc_avc"])
def test_nvenc_output_fps_uses_fruc(name):
    cmd = build(name, video_settings=vs(output_fps="60"))
    assert value_after(cmd, "--vpp-fruc") == "fps=60/1"
    assert "--vpp-fps" not in cmd


@pytest.mark.parametrize("name", [x for x in BUILDERS if not x.startswith("nvenc")])
def test_other_vendors_skip_output_fps(name):
    cmd = build(name, video_settings=vs(output_fps="60"))
    for flag in ("--vpp-fps", "--vpp-fruc", "--vpp-frc"):
        assert flag not in cmd


# Item 6: options the docs restrict to other codecs are not emitted


def test_nvenc_tier_hevc_only():
    assert value_after(build("nvencc_hevc", tier="main"), "--tier") == "main"
    assert "--tier" not in build("nvencc_av1", tier="high")
    assert "--tier" not in build("nvencc_avc")


def test_vce_av1_has_no_hevc_avc_only_options():
    cmd = build("vceencc_av1", vbaq=True, mv_precision="q-pel")
    assert "--vbaq" not in cmd
    assert "--motion-est" not in cmd


@pytest.mark.parametrize("name", ["vceencc_hevc", "vceencc_avc"])
def test_vce_hevc_avc_keep_vbaq_and_motion_est(name):
    cmd = build(name, vbaq=True, mv_precision="half-pel")
    assert "--vbaq" in cmd
    assert value_after(cmd, "--motion-est") == "half-pel"


# Item 8: QSV lookahead depth depends on the rate control mode


def _qsv(name, **kwargs):
    return build(name, lookahead="40", **kwargs)


@pytest.mark.parametrize("name", ["qsvencc_hevc", "qsvencc_avc"])
def test_qsv_la_depth_hevc_avc(name):
    assert value_after(_qsv(name, bitrate="5000k"), "--la-depth") == "40"
    assert value_after(_qsv(name, bitrate=None, cqp=23, qp_mode="la-icq"), "--la-depth") == "40"
    assert "--la-depth" not in _qsv(name, bitrate=None, cqp=23, qp_mode="icq")
    assert "--la-depth" not in _qsv(name, bitrate=None, cqp=23, qp_mode="cqp")
    assert "--extbrc" not in _qsv(name, bitrate="5000k")


def test_qsv_la_depth_av1_needs_extbrc_and_bitrate_control():
    cmd = _qsv("qsvencc_av1", bitrate="5000k")
    assert value_after(cmd, "--la-depth") == "40"
    assert "--extbrc" in cmd
    for qp_mode in ("cqp", "icq", "la-icq"):
        cmd = _qsv("qsvencc_av1", bitrate=None, cqp=23, qp_mode=qp_mode)
        assert "--la-depth" not in cmd
        assert "--extbrc" not in cmd


# Item 7: settings that were collected but never emitted


@pytest.mark.parametrize(
    "name,profile,emitted",
    [
        ("nvencc_hevc", "main10", True),
        ("nvencc_hevc", "main444", True),
        ("nvencc_hevc", "auto", False),
        ("nvencc_hevc", "high", False),
        ("nvencc_av1", "high", True),
        ("nvencc_av1", "main10", False),
        ("nvencc_avc", "high", True),
        ("nvencc_avc", "baseline", True),
        ("nvencc_avc", "main10", False),
    ],
)
def test_nvenc_profile(name, profile, emitted):
    cmd = build(name, profile=profile)
    if emitted:
        assert value_after(cmd, "--profile") == profile
    else:
        assert "--profile" not in cmd


@pytest.mark.parametrize("name", ["vceencc_hevc", "vceencc_av1"])
def test_vce_hevc_av1_b_frames(name):
    assert value_after(build(name, b_frames="2"), "--bframes") == "2"
    assert "--bframes" not in build(name)


# Panels

PANELS = {
    "nvencc_hevc": ("NVENCC", "NVEncCSettings"),
    "nvencc_av1": ("NVENCC", "NVEncCAV1Settings"),
    "nvencc_avc": ("NVENCCAVC", "NVEncCAVCSettings"),
    "qsvencc_hevc": ("QSVEnc", "QSVEncCSettings"),
    "qsvencc_av1": ("QSVAV1Enc", "QSVEncCAV1Settings"),
    "qsvencc_avc": ("QSVEncH264", "QSVEncCH264Settings"),
    "vceencc_hevc": ("VCEENCC", "VCEEncCSettings"),
    "vceencc_av1": ("VCEENCC", "VCEEncCAV1Settings"),
    "vceencc_avc": ("VCEENCCAVC", "VCEEncCAVCSettings"),
}


@pytest.fixture(scope="module")
def qapp():
    from PySide6 import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def panel_factory(qapp):
    from unittest import mock

    from PySide6 import QtGui

    def factory(name, **config_values):
        cls_name, settings_name = PANELS[name]
        settings_cls = getattr(enc, settings_name)
        defaults = settings_cls(**config_values)
        app = mock.MagicMock()
        app.fastflix.config.theme = "onyx"
        app.fastflix.config.encoder_opt = lambda profile, opt: getattr(defaults, opt)
        for attr in ("nvencc_devices", "vceencc_devices", "qsvencc_devices"):
            setattr(app.fastflix.config, attr, {0: {"name": "GPU", "encoders": []}})
        app.font.return_value = QtGui.QFont()
        app.fastflix.current_video.current_video_stream.bit_depth = 8
        module = importlib.import_module(f"fastflix.encoders.{name}.settings_panel")
        panel = getattr(module, cls_name)(None, mock.MagicMock(), app)
        return panel, app

    return factory


def collected(panel, app):
    panel.update_video_encoder_settings()
    return app.fastflix.current_video.video_settings.video_encoder_settings


def test_nvenc_av1_panel_has_no_tier(panel_factory):
    panel, _ = panel_factory("nvencc_av1")
    assert "tier" not in panel.widgets
    for name in ("nvencc_hevc", "nvencc_avc"):
        other, _ = panel_factory(name)
        assert ("tier" in other.widgets) == (name == "nvencc_hevc")


def test_vce_av1_panel_has_no_vbaq_or_motion_est(panel_factory):
    panel, _ = panel_factory("vceencc_av1")
    assert "vbaq" not in panel.widgets
    assert "mv_precision" not in panel.widgets


@pytest.mark.parametrize("name", ["nvencc_hevc", "nvencc_av1", "nvencc_avc"])
def test_nvenc_panel_profile_roundtrip(panel_factory, name):
    panel, app = panel_factory(name)
    options = [panel.widgets.profile.itemText(i) for i in range(panel.widgets.profile.count())]
    assert options[0] == "auto"
    assert options[1:] == list(NVENC_PROFILES[name.split("_")[1]])
    assert collected(panel, app).profile == "auto"
    panel.widgets.profile.setCurrentText(options[-1])
    assert collected(panel, app).profile == options[-1]


@pytest.mark.parametrize("name", ["vceencc_hevc", "vceencc_av1"])
def test_vce_panel_b_frames(panel_factory, name):
    panel, app = panel_factory(name)
    assert collected(panel, app).b_frames is None
    panel.widgets.b_frames.setCurrentText("2")
    assert collected(panel, app).b_frames == "2"


# Item 11: NVEncC --tune


@pytest.mark.parametrize(
    "name,tune,emitted",
    [
        ("nvencc_hevc", "uhq", True),
        ("nvencc_hevc", "lowlatency", True),
        ("nvencc_hevc", "ultralowlatency", True),
        ("nvencc_hevc", "lossless", True),
        ("nvencc_hevc", "hq", False),
        ("nvencc_av1", "uhq", True),
        ("nvencc_av1", "lowlatency", True),
        ("nvencc_av1", "lossless", False),
        ("nvencc_avc", "lowlatency", True),
        ("nvencc_avc", "lossless", True),
        ("nvencc_avc", "uhq", False),
        ("nvencc_hevc", "bogus", False),
    ],
)
def test_nvenc_tune(name, tune, emitted):
    cmd = build(name, tune=tune)
    if emitted:
        assert value_after(cmd, "--tune") == tune
    else:
        assert "--tune" not in cmd


@pytest.mark.parametrize("settings_name", ["NVEncCSettings", "NVEncCAV1Settings", "NVEncCAVCSettings"])
def test_nvenc_tune_defaults_and_old_profiles_load(settings_name):
    cls = getattr(enc, settings_name)
    assert cls().tune == "hq"
    old = cls().model_dump()
    del old["tune"]
    assert cls.model_validate(old).tune == "hq"


@pytest.mark.parametrize("name", ["nvencc_hevc", "nvencc_av1", "nvencc_avc"])
def test_nvenc_panel_tune_roundtrip(panel_factory, name):
    panel, app = panel_factory(name)
    options = [panel.widgets.tune.itemText(i) for i in range(panel.widgets.tune.count())]
    assert options == list(NVENC_TUNES[name.split("_")[1]])
    assert options[0] == "hq"
    assert collected(panel, app).tune == "hq"
    panel.widgets.tune.setCurrentText(options[1])
    assert collected(panel, app).tune == options[1]
