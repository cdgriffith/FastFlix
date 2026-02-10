# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import VVCSettings
from fastflix.models.fastflix import FastFlix
from fastflix.shared import clean_file_string, quoted_path

vvc_valid_color_primaries = [
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

vvc_valid_color_transfers = [
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

vvc_valid_color_matrix = [
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


def build(fastflix: FastFlix):
    settings: VVCSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libvvenc")

    if settings.tier:
        beginning.extend(["-tier:v", settings.tier])

    if settings.levelidc:
        beginning.extend(["-level", settings.levelidc])

    if not settings.subjopt:
        beginning.extend(["-qpa", "0"])

    if settings.period is not None:
        beginning.extend(["-period", str(settings.period)])

    if settings.threads > 0:
        beginning.extend(["-threads", str(settings.threads)])

    vvc_params = settings.vvc_params.copy() or []

    if settings.ifp:
        vvc_params.append("ifp=1")

    if fastflix.current_video.video_settings.maxrate:
        vvc_params.append(f"vbv-maxrate={fastflix.current_video.video_settings.maxrate}")
        vvc_params.append(f"vbv-bufsize={fastflix.current_video.video_settings.bufsize}")

    if not fastflix.current_video.video_settings.remove_hdr:
        # Color primaries/transfer/matrix via FFmpeg flags (libvvenc reads these for VUI)
        if fastflix.current_video.video_settings.color_primaries:
            beginning.extend(["-color_primaries", fastflix.current_video.video_settings.color_primaries])
        elif fastflix.current_video.color_primaries:
            cp = fastflix.current_video.color_primaries
            cp = color_primaries_mapping.get(cp, cp)
            if cp in vvc_valid_color_primaries:
                beginning.extend(["-color_primaries", cp])

        if fastflix.current_video.video_settings.color_transfer:
            beginning.extend(["-color_trc", fastflix.current_video.video_settings.color_transfer])
        elif fastflix.current_video.color_transfer:
            ct = fastflix.current_video.color_transfer
            ct = color_transfer_mapping.get(ct, ct)
            if ct in vvc_valid_color_transfers:
                beginning.extend(["-color_trc", ct])

        if fastflix.current_video.video_settings.color_space:
            beginning.extend(["-colorspace", fastflix.current_video.video_settings.color_space])
        elif fastflix.current_video.color_space:
            cs = fastflix.current_video.color_space
            cs = color_matrix_mapping.get(cs, cs)
            if cs in vvc_valid_color_matrix:
                beginning.extend(["-colorspace", cs])

        if settings.pix_fmt in ("yuv420p10le",):
            if fastflix.current_video.master_display:
                # vvenc format: Gx,Gy,Bx,By,Rx,Ry,WPx,WPy,Lmax,Lmin (bare numbers, comma-separated)
                md = fastflix.current_video.master_display
                md_values = ",".join(v.strip("()") for v in [md.green, md.blue, md.red, md.white, md.luminance])
                vvc_params.append(f"MasteringDisplayColourVolume={md_values}")

            if fastflix.current_video.cll:
                vvc_params.append(f"MaxContentLightLevel={fastflix.current_video.cll}")

        current_chroma_loc = fastflix.current_video.current_video_stream.get("chroma_location")
        if current_chroma_loc in chromaloc_mapping:
            beginning.extend(["-chroma_sample_location", str(chromaloc_mapping[current_chroma_loc])])

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    def get_vvc_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = vvc_params + list(params)
        return ["-vvenc-params", ":".join(all_params)] if all_params else []

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        params = get_vvc_params(["pass=1", f"rcstatsfile={quoted_path(clean_file_string(str(pass_log_file)))}"])
        command_1 = (
            beginning
            + params
            + ["-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-preset:v", settings.preset]
            + extra_both
            + ["-an", "-sn", "-dn"]
            + output_fps
            + ["-f", "mp4", null]
        )
        params2 = get_vvc_params(["pass=2", f"rcstatsfile={quoted_path(clean_file_string(str(pass_log_file)))}"])
        command_2 = (
            beginning
            + params2
            + ["-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-preset:v", settings.preset]
            + extra
            + ending
        )
        return [
            Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
        ]

    elif settings.qp:
        command = (
            beginning
            + get_vvc_params()
            + ["-qp:v", str(settings.qp), "-b:v", "0", "-preset:v", settings.preset]
            + extra
            + ending
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
