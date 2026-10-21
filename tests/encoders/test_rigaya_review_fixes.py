# -*- coding: utf-8 -*-
"""Regression tests for the NVEncC / QSVEncC / VCEEncC review fixes (checked against rigaya's option docs)."""

import importlib
from pathlib import Path

import pytest
from box import Box

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
