# -*- coding: utf-8 -*-
# Shared helpers for FFmpeg's hevc_nvenc / av1_nvenc. Option names verified against
# https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/nvenc_hevc.c and nvenc_av1.c

# FFmpeg 9.0 removed the deprecated NVENC presets, they are aliases of these p1-p7 presets plus a tune
# (see NVENC_DEPRECATED_PRESET aliases in libavcodec/nvenc.c of FFmpeg 8.0)
LEGACY_PRESETS = {
    "default": ("p4", None),
    "hp": ("p1", None),
    "hq": ("p7", None),
    "bd": ("p5", None),
    "ll": ("p4", "ll"),
    "llhp": ("p1", "ll"),
    "llhq": ("p7", "ll"),
    "lossless": ("p4", "lossless"),
    "losslesshp": ("p1", "lossless"),
}

LEGACY_RC = {
    "vbr_minqp": "vbr",
    "vbr_2pass": "vbr",
    "vbr_hq": "vbr",
    "ll_2pass_quality": "vbr",
    "ll_2pass_size": "vbr",
    "cbr_hq": "cbr",
    "cbr_ld_hq": "cbr",
}


def migrate_legacy_options(data):
    """Rewrite removed NVENC preset / rate control values (from old profiles and queues) to supported ones."""
    if not isinstance(data, dict):
        return data
    data = dict(data)
    if data.get("preset") in LEGACY_PRESETS:
        data["preset"], tune = LEGACY_PRESETS[data["preset"]]
        if tune:
            data["tune"] = tune
    if data.get("rc") in LEGACY_RC:
        data["rc"] = LEGACY_RC[data["rc"]]
    return data


def advanced_args(settings) -> list[str]:
    """Arguments for the optional NVENC settings, nothing is emitted for default values."""
    args = []
    if settings.tf_level != "default":
        args.extend(["-tf_level", settings.tf_level])
    if settings.lookahead_level != "default":
        args.extend(["-lookahead_level", settings.lookahead_level])
    if settings.split_encode_mode != "default":
        args.extend(["-split_encode_mode", settings.split_encode_mode])
    if settings.weighted_pred:
        args.extend(["-weighted_pred", "1"])
    if getattr(settings, "unidir_b", False):
        args.extend(["-unidir_b", "1"])
    if settings.no_scenecut:
        args.extend(["-no-scenecut", "1"])
    return args


def uses_cq(settings) -> bool:
    return not settings.bitrate and settings.cq > 0
