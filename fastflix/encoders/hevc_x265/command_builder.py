# -*- coding: utf-8 -*-
import re
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import x265Settings
from fastflix.models.fastflix import FastFlix

x265_valid_color_primaries = [
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

x265_valid_color_transfers = [
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

x265_valid_color_matrix = [
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
    settings: x265Settings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libx265")

    if settings.tune and settings.tune != "default":
        beginning += f"-tune:v {settings.tune} "

    if settings.profile and settings.profile != "default":
        beginning += f"-profile:v {settings.profile} "

    # if settings.gop_size:
    #     beginning += f"-g {settings.gop_size}"

    x265_params = settings.x265_params.copy() or []

    x265_params.append(f"aq-mode={settings.aq_mode}")
    x265_params.append(f"repeat-headers={'1' if settings.repeat_headers else '0'}")
    x265_params.append(f"{'' if settings.intra_smoothing else 'no-'}strong-intra-smoothing=1")
    x265_params.append(f"bframes={settings.bframes}")
    x265_params.append(f"b-adapt={settings.b_adapt}")
    x265_params.append(f"frame-threads={settings.frame_threads}")

    if not fastflix.current_video.video_settings.remove_hdr:
        if fastflix.current_video.video_settings.color_primaries:
            x265_params.append(f"colorprim={fastflix.current_video.video_settings.color_primaries}")
        elif fastflix.current_video.color_primaries:
            if fastflix.current_video.color_primaries in x265_valid_color_primaries:
                x265_params.append(f"colorprim={fastflix.current_video.color_primaries}")
            elif fastflix.current_video.color_primaries in color_primaries_mapping:
                x265_params.append(f"colorprim={color_primaries_mapping[fastflix.current_video.color_primaries]}")

        if fastflix.current_video.video_settings.color_transfer:
            x265_params.append(f"transfer={fastflix.current_video.video_settings.color_transfer}")
        elif fastflix.current_video.color_transfer:
            if fastflix.current_video.color_transfer in x265_valid_color_transfers:
                x265_params.append(f"transfer={fastflix.current_video.color_transfer}")
            elif fastflix.current_video.color_transfer in color_transfer_mapping:
                x265_params.append(f"transfer={color_transfer_mapping[fastflix.current_video.color_transfer]}")

        if fastflix.current_video.video_settings.color_space:
            x265_params.append(f"colormatrix={fastflix.current_video.video_settings.color_space}")
        elif fastflix.current_video.color_space:
            if fastflix.current_video.color_space in x265_valid_color_matrix:
                x265_params.append(f"colormatrix={fastflix.current_video.color_space}")
            elif fastflix.current_video.color_space in color_matrix_mapping:
                x265_params.append(f"colormatrix={color_matrix_mapping[fastflix.current_video.color_space]}")

        if settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
            x265_params.append(f"hdr10_opt={'1' if settings.hdr10_opt else '0'}")

            if fastflix.current_video.master_display:
                settings.hdr10 = True
                x265_params.append(
                    "master-display="
                    f"G{fastflix.current_video.master_display.green}"
                    f"B{fastflix.current_video.master_display.blue}"
                    f"R{fastflix.current_video.master_display.red}"
                    f"WP{fastflix.current_video.master_display.white}"
                    f"L{fastflix.current_video.master_display.luminance}"
                )

            if fastflix.current_video.cll:
                settings.hdr10 = True
                x265_params.append(f"max-cll={fastflix.current_video.cll}")

            x265_params.append(f"hdr10={'1' if settings.hdr10 else '0'}")

        current_chroma_loc = fastflix.current_video.current_video_stream.get("chroma_location")
        if current_chroma_loc in chromaloc_mapping:
            x265_params.append(f"chromaloc={chromaloc_mapping[current_chroma_loc]}")

    if settings.hdr10plus_metadata:
        x265_params.append(f"dhdr10-info='{settings.hdr10plus_metadata}'")
        if settings.dhdr10_opt:
            x265_params.append(f"dhdr10_opt=1")

    if settings.intra_encoding:
        x265_params.append("keyint=1")

    if settings.intra_refresh:
        x265_params.append("intra-refresh=1")

    if settings.lossless:
        x265_params.append("lossless=1")

    if fastflix.current_video.video_settings.maxrate:
        x265_params.append(f"vbv-maxrate={fastflix.current_video.video_settings.maxrate}")
        x265_params.append(f"vbv-bufsize={fastflix.current_video.video_settings.bufsize}")

    if fastflix.current_video.cll:
        pass

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    def get_x265_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = x265_params + list(params)
        return '-x265-params "{}" '.format(":".join(all_params)) if all_params else ""

    if settings.bitrate:
        if settings.bitrate_passes == 2:
            command_1 = (
                f'{beginning} {get_x265_params(["pass=1", "no-slow-firstpass=1"])} '
                f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra if settings.extra_both_passes else ""} '
                f" -an -sn -dn {output_fps} -f mp4 {null}"
            )
            command_2 = (
                f'{beginning} {get_x265_params(["pass=2"])} -passlogfile "{pass_log_file}" '
                f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} {ending}"
            )
            return [
                Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
                Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
            ]
        else:
            command = f"{beginning} {get_x265_params()} -b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} {ending}"
            return [Command(command=command, name="Single pass bitrate", exe="ffmpeg")]

    elif settings.crf:
        command = (
            f"{beginning} {get_x265_params()}  -crf:v {settings.crf} "
            f"-preset:v {settings.preset} {settings.extra} {ending}"
        )
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
