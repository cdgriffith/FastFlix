# -*- coding: utf-8 -*-
import re
import secrets

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
        beginning += f"-tier:v {settings.tier} "

    if settings.levelidc:
        beginning += f"-level {settings.levelidc} "

    vvc_params = settings.vvc_params.copy() or []

    if fastflix.current_video.video_settings.maxrate:
        vvc_params.append(f"vbv-maxrate={fastflix.current_video.video_settings.maxrate}")
        vvc_params.append(f"vbv-bufsize={fastflix.current_video.video_settings.bufsize}")

    if fastflix.current_video.cll:
        pass

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    def get_vvc_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = vvc_params + list(params)
        return '-vvenc-params "{}" '.format(":".join(all_params)) if all_params else ""

    if settings.bitrate:
        params = get_vvc_params(["pass=1", f"rcstatsfile={quoted_path(clean_file_string(pass_log_file))}"])
        command_1 = (
            f"{beginning} {params} "
            f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} '
            f'-preset:v {settings.preset} {settings.extra if settings.extra_both_passes else ""} '
            f" -an -sn -dn {output_fps} -f mp4 {null}"
        )
        params2 = get_vvc_params(["pass=2", f"rcstatsfile={quoted_path(clean_file_string(pass_log_file))}"])
        command_2 = (
            f'{beginning} {params2} -passlogfile "{pass_log_file}" '
            f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} {ending}"
        )
        return [
            Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
        ]

    elif settings.qp:
        command = (
            f"{beginning} {get_vvc_params()}  -qp:v {settings.qp} -b:v 0 "
            f"-preset:v {settings.preset} {settings.extra} {ending}"
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
