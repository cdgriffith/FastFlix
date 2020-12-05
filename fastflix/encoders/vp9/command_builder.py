# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import VP9Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: VP9Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending = generate_all(fastflix, "libvpx-vp9")

    beginning += f'{"-row-mt 1" if settings.row_mt else ""} '

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    if not fastflix.current_video.video_settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
        if fastflix.current_video.color_space.startswith("bt2020"):
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -color_range 1"

    beginning = re.sub("[ ]+", " ", beginning)

    details = f"-quality {settings.quality} -speed {settings.speed} -profile {settings.profile}"

    if settings.bitrate:
        command_1 = f"{beginning} -b:v {settings.bitrate} {details} -pass 1 -an -f webm {null}"
        command_2 = f"{beginning} -b:v {settings.bitrate} {details} -pass 2 {ending}"

    elif settings.crf:
        command_1 = f"{beginning} -b:v 0 -crf {settings.crf} {details} -pass 1 -an -f webm {null}"
        command_2 = (
            f"{beginning} -b:v 0 -crf {settings.crf} {details} "
            f'{"-pass 2" if not settings.single_pass else ""} {ending}'
        )

    else:
        return []

    if settings.crf and settings.single_pass:
        return [Command(command_2, ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")]
    pass_type = "bitrate" if settings.bitrate else "CRF"

    return [
        Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
        Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
    ]
