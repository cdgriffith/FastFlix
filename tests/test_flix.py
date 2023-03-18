# -*- coding: utf-8 -*-
from pathlib import Path

from fastflix.rigaya_helpers import (
    parse_vce_devices,
    VCEEncoder,
    parse_nvenc_devices,
    NVENCEncoder,
    QSVEncoder,
    parse_qsv_devices,
)

here = Path(__file__).parent
assets = here / "assets"

test_logs = {
    "vce": [
        {
            "text": (assets / "rigaya_vce_cf_5800h_win10.txt").read_text(encoding="utf-8").splitlines(),
            "result": VCEEncoder(device_number=0, device_name="AMD Radeon", formats=["H.264/AVC", "H.265/HEVC"]),
        }
    ],
    "nvenc": [
        {
            "text": (assets / "rigaya_nvenc_cf_3060_linux.txt").read_text(encoding="utf-8").splitlines(),
            "result": NVENCEncoder(
                device_number=0, device_name="NVIDIA GeForce RTX 3060", formats=["H.264/AVC", "H.265/HEVC"]
            ),
        }
    ],
    "qsv": [
        {
            "text": (assets / "rigaya_qsv_cf_i5_9400_win10.txt").read_text(encoding="utf-8").splitlines(),
            "result": QSVEncoder(
                device_number=0,
                device_name="Intel UHD Graphics 630",
                formats=["H.264/AVC PG", "H.264/AVC FF", "H.265/HEVC PG", "MPEG2 PG", "MPEG2 FF"],
            ),
        }
    ],
}


def test_parse_vce():
    for vce_test in test_logs["vce"]:
        assert parse_vce_devices(vce_test["text"]) == vce_test["result"]


def test_nvenc_parse():
    for nvenc_test in test_logs["nvenc"]:
        assert parse_nvenc_devices(nvenc_test["text"]) == nvenc_test["result"]


def test_qsv_parse():
    for qsv_test in test_logs["qsv"]:
        assert parse_qsv_devices(qsv_test["text"]) == qsv_test["result"]
