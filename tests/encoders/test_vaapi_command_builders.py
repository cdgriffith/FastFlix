# -*- coding: utf-8 -*-
import importlib
from pathlib import Path

import pytest

from fastflix.encoders.common.helpers import generate_filters
from fastflix.models import encode
from fastflix.models.video import Crop, VideoSettings

from tests.conftest import create_fastflix_instance

ENCODERS = {
    "vaapi_h264": ("VAAPIH264Settings", True),
    "vaapi_hevc": ("VAAPIHEVCSettings", True),
    "vaapi_vp9": ("VAAPIVP9Settings", False),
    "vaapi_mpeg2": ("VAAPIMPEG2Settings", False),
}
ALL = list(ENCODERS)
EXPLICIT_QP = [k for k, v in ENCODERS.items() if v[1]]
GLOBAL_QUALITY_ONLY = [k for k, v in ENCODERS.items() if not v[1]]


def run_build(name, settings_kwargs=None, **video_kwargs):
    cls_name = ENCODERS[name][0]
    settings = getattr(encode, cls_name)(**(settings_kwargs or {}))
    video_kwargs.setdefault("remove_hdr", False)
    fastflix = create_fastflix_instance(
        encoder_settings=settings,
        video_settings=VideoSettings(maxrate=None, bufsize=None, **video_kwargs),
    )
    module = importlib.import_module(f"fastflix.encoders.{name}.command_builder")
    return module.build(fastflix)[0].command


def filter_complex(cmd):
    return cmd[cmd.index("-filter_complex") + 1]


def opt(cmd, flag):
    return cmd[cmd.index(flag) + 1]


@pytest.mark.parametrize("name", ALL)
def test_low_power_uses_underscore_option(name):
    cmd = run_build(name, {"low_power": True})
    assert "-low_power" in cmd
    assert opt(cmd, "-low_power") == "1"
    assert "-low-power" not in cmd


@pytest.mark.parametrize("name", ALL)
def test_software_frames_pipeline_is_robust(name):
    """No forced hw output frames and no hwdownload, so a software-decode fallback still works."""
    cmd = run_build(name)
    assert "-hwaccel_output_format" not in cmd
    assert "hwdownload" not in filter_complex(cmd)
    assert filter_complex(cmd) == "[0:0]format=nv12,hwupload[v]"
    assert "-filter_hw_device" in cmd
    assert opt(cmd, "-filter_hw_device") == "hwdev"


@pytest.mark.parametrize("name", ALL)
def test_scale_is_applied(name):
    cmd = run_build(name, resolution_method="custom", resolution_custom="1280:720")
    fc = filter_complex(cmd)
    assert fc.startswith("[0:0]scale=1280:720:flags=")
    assert fc.endswith(",format=nv12,hwupload[v]")


@pytest.mark.parametrize("name", ALL)
def test_crop_and_rotate_run_before_upload(name):
    cmd = run_build(name, crop=Crop(top=10, bottom=10, left=20, right=20), rotate=1)
    fc = filter_complex(cmd)
    assert fc.index("crop=") < fc.index("transpose=1") < fc.index("hwupload")
    assert "hwdownload" not in fc


@pytest.mark.parametrize("name", ALL)
def test_level_auto_is_not_emitted(name):
    cls = getattr(encode, ENCODERS[name][0])
    if "level" not in cls.model_fields:
        pytest.skip("no level")
    cmd = run_build(name, {"level": "auto"})
    assert "-level" not in cmd
    cmd = run_build(name, {"level": "4.1"})
    assert opt(cmd, "-level") == "4.1"


@pytest.mark.parametrize("name", ["vaapi_hevc", "vaapi_vp9"])
def test_ten_bit_uploads_p010_and_sets_profile(name):
    cmd = run_build(name, {"bit_depth": "10-bit"})
    assert filter_complex(cmd) == "[0:0]format=p010le,hwupload[v]"
    assert opt(cmd, "-profile:v") == ("main10" if name == "vaapi_hevc" else "2")


@pytest.mark.parametrize("name", ["vaapi_hevc", "vaapi_vp9"])
def test_eight_bit_default_profile(name):
    cmd = run_build(name)
    assert filter_complex(cmd) == "[0:0]format=nv12,hwupload[v]"
    assert opt(cmd, "-profile:v") == ("main" if name == "vaapi_hevc" else "0")


@pytest.mark.parametrize("name", ["vaapi_h264", "vaapi_mpeg2"])
def test_eight_bit_only_encoders_have_no_bit_depth_or_profile(name):
    cmd = run_build(name)
    assert "-profile:v" not in cmd
    assert "p010le" not in filter_complex(cmd)


def test_legacy_settings_without_bit_depth_default_to_8_bit():
    restored = encode.VAAPIHEVCSettings.model_validate({"name": "VAAPI HEVC", "qp": 20})
    assert restored.bit_depth == "8-bit"


@pytest.mark.parametrize("name", ALL)
def test_tonemap_vaapi_gets_p010_input(name):
    cmd = run_build(name, remove_hdr=True)
    assert filter_complex(cmd) == ("[0:0]format=p010le,hwupload,tonemap_vaapi=format=nv12:p=bt709:t=bt709:m=bt709[v]")


def test_tonemap_vaapi_keeps_requested_10_bit_output():
    cmd = run_build("vaapi_hevc", {"bit_depth": "10-bit"}, remove_hdr=True)
    assert "tonemap_vaapi=format=p010:" in filter_complex(cmd)


def test_vaapi_upload_comes_after_burned_in_text_subtitles():
    result = generate_filters(
        selected_track=0,
        source=Path("input.mkv"),
        vaapi=True,
        burn_in_subtitle_track=0,
        burn_in_subtitle_type="text",
        custom_filters="hue=s=0.5",
    )
    fc = result[1]
    assert fc.index("hue=") < fc.index("subtitles=") < fc.index("hwupload")


@pytest.mark.parametrize("name", EXPLICIT_QP)
def test_cqp_uses_qp(name):
    cmd = run_build(name, {"rc_mode": "CQP", "qp": 24})
    assert opt(cmd, "-rc_mode") == "CQP"
    assert opt(cmd, "-qp") == "24"
    assert "-global_quality" not in cmd


@pytest.mark.parametrize("name", GLOBAL_QUALITY_ONLY)
def test_encoders_without_qp_option_use_global_quality(name):
    cmd = run_build(name, {"rc_mode": "CQP", "qp": 24})
    assert "-qp" not in cmd
    assert opt(cmd, "-global_quality") == "24"


@pytest.mark.parametrize("name", ALL)
def test_icq_uses_global_quality(name):
    cmd = run_build(name, {"rc_mode": "ICQ", "qp": 22})
    assert opt(cmd, "-rc_mode") == "ICQ"
    assert opt(cmd, "-global_quality") == "22"
    assert "-qp" not in cmd
    assert "-b:v" not in cmd


@pytest.mark.parametrize("name", ALL)
def test_qvbr_uses_bitrate_and_global_quality(name):
    cmd = run_build(name, {"rc_mode": "QVBR", "qp": 22, "bitrate": "4000k"})
    assert opt(cmd, "-rc_mode") == "QVBR"
    assert opt(cmd, "-global_quality") == "22"
    assert opt(cmd, "-b:v") == "4000k"
    assert "-qp" not in cmd


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("mode", ["CQP", "ICQ"])
def test_quality_modes_do_not_emit_bitrate(name, mode):
    cmd = run_build(name, {"rc_mode": mode, "qp": None, "bitrate": "5000k"})
    assert "-rc_mode" not in cmd
    assert opt(cmd, "-b:v") == "5000k"


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("mode", ["CBR", "VBR", "AVBR", "QVBR"])
def test_bitrate_modes_with_bitrate(name, mode):
    cmd = run_build(name, {"rc_mode": mode, "qp": None, "bitrate": "5000k"})
    assert opt(cmd, "-rc_mode") == mode
    assert opt(cmd, "-b:v") == "5000k"
    assert "-qp" not in cmd


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("mode", ["CBR", "VBR", "AVBR", "QVBR"])
def test_bitrate_modes_without_bitrate_fall_back_to_auto(name, mode):
    cmd = run_build(name, {"rc_mode": mode, "qp": 26, "bitrate": None})
    assert "-rc_mode" not in cmd
    assert "-b:v" not in cmd
    assert "-qp" in cmd or "-global_quality" in cmd


@pytest.mark.parametrize("name", ALL)
def test_auto_with_qp_and_bitrate(name):
    cmd = run_build(name, {"rc_mode": "auto", "qp": 26})
    assert opt(cmd, "-rc_mode") == "auto"
    assert "-b:v" not in cmd
