# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass
from typing import Optional, Tuple

HDR_BIT_DEPTHS = (10, 12)

valid_color_primaries = [
    "bt709",
    "unknown",
    "reserved",
    "bt470m",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "film",
    "bt2020",
    "smpte428",
    "smpte431",
    "smpte432",
]

valid_color_transfers = [
    "bt709",
    "unknown",
    "reserved",
    "bt470m",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "linear",
    "log100",
    "log316",
    "iec61966-2-4",
    "bt1361e",
    "iec61966-2-1",
    "bt2020-10",
    "bt2020-12",
    "smpte2084",
    "smpte428",
    "arib-std-b67",
]

valid_color_matrix = [
    "gbr",
    "bt709",
    "unknown",
    "reserved",
    "fcc",
    "bt470bg",
    "smpte170m",
    "smpte240m",
    "ycgco",
    "bt2020nc",
    "bt2020c",
    "smpte2085",
    "chroma-derived-nc",
    "chroma-derived-c",
    "ictcp",
]

color_primaries_mapping = {"smpte428_1": "smpte428"}

color_transfer_mapping = {
    "iec61966_2_4": "iec61966-2-4",
    "iec61966_2_1": "iec61966-2-1",
    "bt2020_10": "bt2020-10",
    "bt2020_10bit": "bt2020-10",
    "bt2020_12": "bt2020-12",
    "bt2020_12bit": "bt2020-12",
    "smpte428_1": "smpte428",
}

color_matrix_mapping = {"bt2020_ncl": "bt2020nc", "bt2020_cl": "bt2020c"}

chromaloc_mapping = {"left": 0, "center": 1, "topleft": 2, "top": 3, "bottomleft": 4, "bottom": 5}


def get_bit_depth(pix_fmt: Optional[str]) -> int:
    """Bit depth encoded in an ffmpeg pix_fmt name (yuv422p10le, p010le, ...); 8 when none is present."""
    if not pix_fmt:
        return 8
    match = re.search(r"p0?(\d{2})(?:le|be)?$", pix_fmt)
    return int(match.group(1)) if match else 8


def is_hdr_bit_depth(pix_fmt: Optional[str]) -> bool:
    """True for 10/12 bit formats of any chroma subsampling."""
    return get_bit_depth(pix_fmt) in HDR_BIT_DEPTHS


def _pair(value: str) -> Tuple[str, str]:
    first, second = str(value).strip().strip("()").split(",")
    return first.strip(), second.strip()


@dataclass(frozen=True)
class MasterDisplay:
    """Mastering display metadata as stored by flix.convert_mastering_display.

    Chromaticities are in 1/50000 units, luminance in 1/10000 cd/m2 units; values are kept as the stored tokens.
    """

    green: Tuple[str, str]
    blue: Tuple[str, str]
    red: Tuple[str, str]
    white: Tuple[str, str]
    luminance: Tuple[str, str]

    def to_x265(self) -> str:
        return (
            f"G({','.join(self.green)})B({','.join(self.blue)})R({','.join(self.red)})"
            f"WP({','.join(self.white)})L({','.join(self.luminance)})"
        )

    def to_rav1e(self) -> str:
        # librav1e does not read this through rav1e-params (it only logs a warning); kept as previously emitted
        return self.to_x265()

    def to_svt_av1(self) -> str:
        def scale(pair, rate=50_000):
            return ",".join(f"{float(v) / rate:0.4f}" for v in pair)

        return (
            f"G({scale(self.green)})B({scale(self.blue)})R({scale(self.red)})"
            f"WP({scale(self.white)})L({scale(self.luminance, 10_000)})"
        )

    def to_vvenc(self) -> str:
        """vvenc MasteringDisplayColourVolume: Gx,Gy,Bx,By,Rx,Ry,WPx,WPy,Lmax,Lmin"""
        return ",".join(",".join(p) for p in (self.green, self.blue, self.red, self.white, self.luminance))


def parse_master_display(master_display) -> Optional[MasterDisplay]:
    if not master_display:
        return None
    return MasterDisplay(
        green=_pair(master_display.green),
        blue=_pair(master_display.blue),
        red=_pair(master_display.red),
        white=_pair(master_display.white),
        luminance=_pair(master_display.luminance),
    )
