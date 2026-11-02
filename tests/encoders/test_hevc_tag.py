# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from fastflix.encoders.common.helpers import hevc_tag_args
from fastflix.encoders.ffmpeg_hevc_nvenc.command_builder import build as nvenc_build
from fastflix.encoders.hevc_videotoolbox.command_builder import build as vt_build
from fastflix.encoders.hevc_x265.command_builder import build as x265_build
from fastflix.encoders.vaapi_hevc.command_builder import build as vaapi_build
from fastflix.models.encode import FFmpegNVENCSettings, HEVCVideoToolboxSettings, VAAPIHEVCSettings, x265Settings
from fastflix.models.video import VideoSettings
from tests.conftest import create_fastflix_instance

TAG = ["-tag:v", "hvc1"]


@pytest.mark.parametrize("name", ["out.mp4", "out.MP4", "out.m4v", "out.mov", Path("a/b/out.mp4")])
def test_tag_for_apple_containers(name):
    assert hevc_tag_args(name) == TAG


@pytest.mark.parametrize("name", ["out.mkv", "out.webm", "out.ts", "", None])
def test_no_tag_for_other_containers(name):
    assert hevc_tag_args(name) == []


def _fastflix(settings, output):
    vs = VideoSettings(remove_hdr=False, maxrate=None, bufsize=None, output_path=Path(output))
    return create_fastflix_instance(encoder_settings=settings, video_settings=vs)


BUILDERS = [
    (nvenc_build, lambda: FFmpegNVENCSettings(bitrate=None, qp=25)),
    (vt_build, lambda: HEVCVideoToolboxSettings(q=50)),
    (vaapi_build, lambda: VAAPIHEVCSettings(qp=26, bitrate=None)),
    (x265_build, lambda: x265Settings(crf=22, bitrate=None)),
]


def _build(builder, settings, output):
    return builder(_fastflix(settings, output))[-1].command


@pytest.mark.parametrize("builder,make", BUILDERS)
@pytest.mark.parametrize("output", ["out.mp4", "out.mov", "out.m4v"])
def test_builders_add_hvc1_for_mp4_family(builder, make, output):
    cmd = _build(builder, make(), output)
    idx = cmd.index("-tag:v")
    assert cmd[idx + 1] == "hvc1"
    assert idx < len(cmd) - 1 and cmd.index(output) > idx


@pytest.mark.parametrize("builder,make", BUILDERS)
def test_builders_no_tag_for_mkv(builder, make):
    cmd = _build(builder, make(), "out.mkv")
    assert "-tag:v" not in cmd
