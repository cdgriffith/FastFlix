# -*- coding: utf-8 -*-
from box import Box
import pytest

from fastflix.encoders.common import hdr_metadata as hm

# Real HDR10 sample, as stored by flix.convert_mastering_display
SAMPLE = Box(
    green="(13250,34500)",
    blue="(7500,3000)",
    red="(34000,16000)",
    white="(15635,16450)",
    luminance="(10000000,1)",
)


@pytest.mark.parametrize(
    "pix_fmt",
    ["yuv420p10le", "yuv420p12le", "yuv422p10le", "yuv422p12le", "yuv444p10le", "yuv444p12le", "p010le", "p012le"],
)
def test_high_bit_depth_formats_are_hdr_capable(pix_fmt):
    assert hm.is_hdr_bit_depth(pix_fmt)


@pytest.mark.parametrize("pix_fmt", ["yuv420p", "yuv422p", "yuv444p", "nv12", "vaapi", "", None, "gray"])
def test_8bit_formats_are_not_hdr_capable(pix_fmt):
    assert not hm.is_hdr_bit_depth(pix_fmt)


def test_parse_master_display():
    md = hm.parse_master_display(SAMPLE)
    assert md.green == ("13250", "34500")
    assert md.luminance == ("10000000", "1")


def test_parse_none():
    assert hm.parse_master_display(None) is None


def test_x265_format():
    md = hm.parse_master_display(SAMPLE)
    assert md.to_x265() == "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)"


def test_svt_av1_format():
    md = hm.parse_master_display(SAMPLE)
    assert md.to_svt_av1() == "G(0.2650,0.6900)B(0.1500,0.0600)R(0.6800,0.3200)WP(0.3127,0.3290)L(1000.0000,0.0001)"


def test_vvenc_format():
    md = hm.parse_master_display(SAMPLE)
    assert md.to_vvenc() == "13250,34500,7500,3000,34000,16000,15635,16450,10000000,1"


def test_rav1e_format_unchanged_raw_x265_style():
    md = hm.parse_master_display(SAMPLE)
    assert md.to_rav1e() == md.to_x265()
