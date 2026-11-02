# -*- coding: utf-8 -*-
from typing import List

QUALITY_MODES = ("CQP", "ICQ")
BITRATE_MODES = ("CBR", "VBR", "AVBR")


def vaapi_sw_format(bit_depth) -> str:
    """Software pixel format frames are converted to before hwupload."""
    return "p010le" if str(bit_depth or "").startswith("10") else "nv12"


def vaapi_level_args(settings) -> List[str]:
    level = getattr(settings, "level", None)
    if not level or str(level).lower() == "auto":
        return []
    return ["-level", str(level)]


def vaapi_rate_control_args(settings, explicit_qp: bool) -> List[str]:
    """Rate control arguments for the *_vaapi encoders.

    CQP uses the encoder's private ``-qp`` where it exists (h264/hevc), ICQ/QVBR (and CQP for encoders without
    ``-qp``) use ``-global_quality``. Combinations that cannot work (a quality mode with only a bitrate, a bitrate
    mode with only a quality) fall back to letting FFmpeg choose the mode from the value that is available.
    """
    mode = str(settings.rc_mode or "auto")
    has_bitrate = bool(settings.bitrate)
    has_quality = settings.qp is not None

    args = []
    if mode in QUALITY_MODES and not has_quality:
        mode = "fallback"
    elif mode in BITRATE_MODES + ("QVBR",) and not has_bitrate:
        mode = "fallback"
    if mode != "fallback":
        args.extend(["-rc_mode", mode])

    if has_bitrate and mode not in QUALITY_MODES:
        args.extend(["-b:v", str(settings.bitrate)])

    use_quality = has_quality and (
        mode in QUALITY_MODES + ("QVBR",) or (mode in ("auto", "fallback") and not has_bitrate)
    )
    if use_quality:
        if mode in ("ICQ", "QVBR") or not explicit_qp:
            args.extend(["-global_quality", str(settings.qp)])
        else:
            args.extend(["-qp", str(settings.qp)])
    return args
