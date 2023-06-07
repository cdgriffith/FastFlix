# -*- coding: utf-8 -*-
import re
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import VP9Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: VP9Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libvpx-vp9")

    beginning += f'{"-row-mt 1" if settings.row_mt else ""} ' f"{generate_color_details(fastflix)} "

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        beginning += f'-passlogfile "{pass_log_file}" '

    # TODO color_range 1
    # if not fastflix.current_video.video_settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
    #     if fastflix.current_video.color_space.startswith("bt2020"):
    #         beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -color_range 1"

    details = f"-quality:v {settings.quality} -profile:v {settings.profile} -tile-columns:v {settings.tile_columns} -tile-rows:v {settings.tile_rows} "

    if settings.bitrate:
        if settings.quality == "realtime":
            return [
                Command(
                    command=f"{beginning} -speed:v {settings.speed} -b:v {settings.bitrate} {details} {settings.extra} {ending} ",
                    name="Single pass realtime bitrate",
                    exe="ffmpeg",
                )
            ]
        command_1 = f"{beginning} -speed:v {'4' if settings.fast_first_pass else settings.speed} -b:v {settings.bitrate} {details} -pass 1 {settings.extra if settings.extra_both_passes else ''} -an {output_fps} -f webm {null}"
        command_2 = (
            f"{beginning} -speed:v {settings.speed} -b:v {settings.bitrate} {details} -pass 2 {settings.extra} {ending}"
        )

    elif settings.crf:
        command_1 = f"{beginning} -b:v 0 -crf:v {settings.crf} {details} -pass 1 {settings.extra if settings.extra_both_passes else ''} -an {output_fps} -f webm {null}"
        command_2 = (
            f"{beginning} -b:v 0 -crf:v {settings.crf} {details} "
            f'{"-pass 2" if not settings.single_pass else ""} {settings.extra} {ending}'
        )

    else:
        return []

    if settings.crf and settings.single_pass:
        return [Command(command=command_2, name="Single pass CRF", exe="ffmpeg")]
    pass_type = "bitrate" if settings.bitrate else "CRF"

    return [
        Command(command=command_1, name=f"First pass {pass_type}", exe="ffmpeg"),
        Command(command=command_2, name=f"Second pass {pass_type} ", exe="ffmpeg"),
    ]
