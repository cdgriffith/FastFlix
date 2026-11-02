# -*- coding: utf-8 -*-
"""Regression tests for PR 740 review findings (encoders)."""

from pathlib import Path
from unittest import mock

import pytest
from box import Box

from fastflix.encoders.common.encc_helpers import build_audio as encc_build_audio
from fastflix.encoders.common.encc_helpers import rigaya_extra_options
from fastflix.models.encode import (
    AOMAV1Settings,
    NVEncCSettings,
    QSVEncCAV1Settings,
    QSVEncCH264Settings,
    QSVEncCSettings,
    SVTAV1Settings,
    sanitize_qsv_tune,
    x264Settings,
)
from fastflix.models.video import AudioTrack, VideoSettings

from tests.conftest import create_fastflix_instance


# ---- 1. QSVEncC tune ----


@pytest.mark.parametrize("old", ["hq", "ll", "ull", "lossless"])
def test_qsv_tune_old_nvencc_values_dropped(old):
    assert sanitize_qsv_tune(old) is None
    assert QSVEncCSettings(tune=old).tune is None
    assert QSVEncCH264Settings(tune=old).tune is None
    assert QSVEncCAV1Settings(tune=old).tune is None


def test_qsv_tune_valid_values_kept():
    assert sanitize_qsv_tune("vmaf") == "vmaf"
    assert sanitize_qsv_tune("psnr,ssim") == "psnr,ssim"
    assert sanitize_qsv_tune("hq,perceptual") == "perceptual"
    assert sanitize_qsv_tune("") is None


def _qsv_fastflix(settings):
    fastflix = create_fastflix_instance(encoder_settings=settings, video_settings=VideoSettings())
    fastflix.current_video.streams = Box(
        {
            "video": [
                Box(
                    {
                        "index": 0,
                        "id": "0x1",
                        "codec_name": "hevc",
                        "codec_type": "video",
                        "pix_fmt": "yuv420p10le",
                        "bit_depth": 10,
                        "r_frame_rate": "24/1",
                        "avg_frame_rate": "24/1",
                        "width": 1920,
                        "height": 1080,
                    }
                )
            ],
            "audio": [],
            "subtitle": [],
        }
    )
    fastflix.config.qsvencc = Path("QSVEncC64")
    return fastflix


def test_qsv_builder_emits_valid_tune_only():
    from fastflix.encoders.qsvencc_hevc.command_builder import build

    with mock.patch("fastflix.encoders.qsvencc_hevc.command_builder.rigaya_auto_options", return_value=[]):
        cmd = build(_qsv_fastflix(QSVEncCSettings(bitrate=None, cqp=22, preset="best", tune="vmaf")))[0].command
        assert cmd[cmd.index("--tune") + 1] == "vmaf"
        settings = QSVEncCSettings(bitrate=None, cqp=22, preset="best")
        settings.tune = "hq"  # bypasses the validator, the builder must still guard
        assert "--tune" not in build(_qsv_fastflix(settings))[0].command


# ---- 7. single --vpp-colorspace ----


def test_hdr2sdr_and_lut3d_merged():
    fastflix = create_fastflix_instance(
        encoder_settings=NVEncCSettings(), video_settings=VideoSettings(lut3d_path="/a/b.cube")
    )
    result = rigaya_extra_options(fastflix.current_video, hdr2sdr="hdr2sdr=hable")
    assert result.count("--vpp-colorspace") == 1
    assert result[result.index("--vpp-colorspace") + 1] == "hdr2sdr=hable,lut3d=/a/b.cube,lut3d_interp=tetrahedral"


def test_hdr2sdr_alone():
    fastflix = create_fastflix_instance(encoder_settings=NVEncCSettings(), video_settings=VideoSettings())
    result = rigaya_extra_options(fastflix.current_video, hdr2sdr="hdr2sdr=mobius")
    assert result[result.index("--vpp-colorspace") + 1] == "hdr2sdr=mobius"


# ---- 8. pad with rotation ----


def _pad(rotate, aspect="16:9", width=1000, height=500):
    fastflix = create_fastflix_instance(
        encoder_settings=NVEncCSettings(), video_settings=VideoSettings(pad_aspect=aspect, rotate=rotate)
    )
    video = fastflix.current_video
    video.streams.video[0].width = width
    video.streams.video[0].height = height
    assert (video.width, video.height) == (width, height)
    result = rigaya_extra_options(video)
    return [int(x) for x in result[result.index("--vpp-pad") + 1].split(",")]


def test_pad_accounts_for_rotation():
    # 1000x500 is wider than 16:9 -> padded top/bottom
    left, top, right, bottom = _pad(0)
    assert left == 0 and right == 0 and top > 0 and bottom > 0
    # rotated 90 degrees -> 500x1000 portrait -> padded left/right up to 16:9 at height 1000
    left, top, right, bottom = _pad(1)
    assert top == 0 and bottom == 0 and left > 0 and right > 0
    assert 500 + left + right == 1778


# ---- 9. GOP ----


@pytest.mark.parametrize("gop", [None, 0, -1])
def test_gop_unset_values(gop):
    fastflix = create_fastflix_instance(encoder_settings=NVEncCSettings(), video_settings=VideoSettings(gop_length=gop))
    assert "--gop-len" not in rigaya_extra_options(fastflix.current_video)


# ---- 3. rigaya audio profile ----


def _audio_track(codec, profile, downmix="stereo"):
    return AudioTrack(
        index=1,
        outdex=1,
        codec="eac3",
        enabled=True,
        conversion_codec=codec,
        conversion_profile=profile,
        conversion_bitrate="64k",
        downmix=downmix,
        raw_info=Box({"channels": 6, "channel_layout": "5.1"}),
        dispositions={},
    )


def test_rigaya_audio_profile_names():
    out = encc_build_audio([_audio_track("libfdk_aac", "aac_he")], [Box({"index": 1})])
    assert "1?HE-AAC" in out
    out = encc_build_audio([_audio_track("libfdk_aac", "aac_he_v2")], [Box({"index": 1})])
    assert "1?HE-AACv2" in out
    out = encc_build_audio([_audio_track("libfdk_aac", "aac_he_v2", downmix="5.1")], [Box({"index": 1})])
    assert "1?HE-AAC" in out


def test_rigaya_native_aac_no_profile():
    out = encc_build_audio([_audio_track("aac", "aac_he")], [Box({"index": 1})])
    assert "--audio-profile" not in out


# ---- 4. x264 lossless ----


def _build_x264(**kwargs):
    from fastflix.encoders.avc_x264.command_builder import build

    fastflix = create_fastflix_instance(
        encoder_settings=x264Settings(crf=23, preset="medium", pix_fmt="yuv420p", bitrate=None, **kwargs),
        video_settings=VideoSettings(),
    )
    with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_all") as gen:
        gen.return_value = (["ffmpeg", "-i", "in.mkv"], ["out.mkv"], [])
        with mock.patch("fastflix.encoders.avc_x264.command_builder.generate_color_details", return_value=[]):
            return build(fastflix)[0].command


def test_x264_lossless_drops_incompatible_profile():
    cmd = _build_x264(profile="high", lossless=True)
    assert "-profile:v" not in cmd
    assert "-qp" in cmd


def test_x264_lossless_keeps_high444():
    cmd = _build_x264(profile="high444", lossless=True)
    assert cmd[cmd.index("-profile:v") + 1] == "high444"


def test_x264_profile_kept_when_not_lossless():
    assert "-profile:v" in _build_x264(profile="high", lossless=False)


# ---- 5. SVT-AV1 lossless ----


def _build_svt(**kwargs):
    from fastflix.encoders.svt_av1.command_builder import build

    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24, qp_mode="crf", speed="7", tile_columns="0", tile_rows="0", single_pass=True, bitrate=None, **kwargs
        ),
        video_settings=VideoSettings(),
    )
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as gen:
        gen.return_value = (["ffmpeg", "-i", "in.mkv"], ["out.mkv"], [])
        with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_color_details", return_value=[]):
            cmd = build(fastflix)[0].command
    return cmd[cmd.index("-svtav1-params") + 1]


def test_svt_lossless_no_film_grain():
    params = _build_svt(lossless=True, film_grain=8, film_grain_denoise=True)
    assert "lossless=1" in params
    assert "film-grain" not in params


def test_svt_film_grain_when_not_lossless():
    assert "film-grain=8" in _build_svt(lossless=False, film_grain=8)


# ---- 6. AOM lossless ----


def _build_aom(**kwargs):
    from fastflix.encoders.av1_aom.command_builder import build

    fastflix = create_fastflix_instance(
        encoder_settings=AOMAV1Settings(
            crf=26,
            cpu_used="4",
            usage="good",
            row_mt="enabled",
            tile_rows="0",
            tile_columns="0",
            bitrate=None,
            **kwargs,
        ),
        video_settings=VideoSettings(),
    )
    with mock.patch("fastflix.encoders.av1_aom.command_builder.generate_all") as gen:
        gen.return_value = (["ffmpeg", "-i", "in.mkv"], ["out.mkv"], [])
        with mock.patch("fastflix.encoders.av1_aom.command_builder.generate_color_details", return_value=[]):
            return build(fastflix)[0].command


def test_aom_lossless_skips_denoise():
    assert "-denoise-noise-level" not in _build_aom(lossless=True, denoise_noise_level=10)


def test_aom_denoise_when_not_lossless():
    assert "-denoise-noise-level" in _build_aom(lossless=False, denoise_noise_level=10)
