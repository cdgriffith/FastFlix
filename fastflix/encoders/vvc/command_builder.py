# -*- coding: utf-8 -*-
import re
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import VVCSettings
from fastflix.models.fastflix import FastFlix

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

    beginning, ending = generate_all(fastflix, "libvvenc")

    if settings.tier:
        beginning += f"-tier:v {settings.tier} "

    if settings.levelidc:
        beginning += f"-levelidc {settings.levelidc} "

    vvc_params = settings.vvc_params.copy() or []


    if not fastflix.current_video.video_settings.remove_hdr:
        if fastflix.current_video.video_settings.color_primaries:
            vvc_params.append(f"colorprim={fastflix.current_video.video_settings.color_primaries}")
        elif fastflix.current_video.color_primaries:
            if fastflix.current_video.color_primaries in vvc_valid_color_primaries:
                vvc_params.append(f"colorprim={fastflix.current_video.color_primaries}")
            elif fastflix.current_video.color_primaries in color_primaries_mapping:
                vvc_params.append(f"colorprim={color_primaries_mapping[fastflix.current_video.color_primaries]}")

        if fastflix.current_video.video_settings.color_transfer:
            vvc_params.append(f"transfer={fastflix.current_video.video_settings.color_transfer}")
        elif fastflix.current_video.color_transfer:
            if fastflix.current_video.color_transfer in vvc_valid_color_transfers:
                vvc_params.append(f"transfer={fastflix.current_video.color_transfer}")
            elif fastflix.current_video.color_transfer in color_transfer_mapping:
                vvc_params.append(f"transfer={color_transfer_mapping[fastflix.current_video.color_transfer]}")

        if fastflix.current_video.video_settings.color_space:
            vvc_params.append(f"colormatrix={fastflix.current_video.video_settings.color_space}")
        elif fastflix.current_video.color_space:
            if fastflix.current_video.color_space in vvc_valid_color_matrix:
                vvc_params.append(f"colormatrix={fastflix.current_video.color_space}")
            elif fastflix.current_video.color_space in color_matrix_mapping:
                vvc_params.append(f"colormatrix={color_matrix_mapping[fastflix.current_video.color_space]}")

            if fastflix.current_video.master_display:
                settings.hdr10 = True
                vvc_params.append(
                    "master-display="
                    f"G{fastflix.current_video.master_display.green}"
                    f"B{fastflix.current_video.master_display.blue}"
                    f"R{fastflix.current_video.master_display.red}"
                    f"WP{fastflix.current_video.master_display.white}"
                    f"L{fastflix.current_video.master_display.luminance}"
                )

            if fastflix.current_video.cll:
                settings.hdr10 = True
                vvc_params.append(f"max-cll={fastflix.current_video.cll}")

            vvc_params.append(f"hdr10={'1' if settings.hdr10 else '0'}")

        current_chroma_loc = fastflix.current_video.current_video_stream.get("chroma_location")
        if current_chroma_loc in chromaloc_mapping:
            vvc_params.append(f"chromaloc={chromaloc_mapping[current_chroma_loc]}")


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
        command_1 = (
            f'{beginning} {get_vvc_params(["pass=1", "no-slow-firstpass=1"])} '
            f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra if settings.extra_both_passes else ""} '
            f" -an -sn -dn -f mp4 {null}"
        )
        command_2 = (
            f'{beginning} {get_vvc_params(["pass=2"])} -passlogfile "{pass_log_file}" '
            f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} {ending}"
        )
        return [
            Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
        ]

    elif settings.qp:
        command = (
            f"{beginning} {get_vvc_params()}  -qp:v {settings.qp} "
            f"-preset:v {settings.preset} {settings.extra} {ending}"
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
