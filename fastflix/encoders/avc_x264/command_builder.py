# -*- coding: utf-8 -*-
import re
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import x264Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: x264Settings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libx264")

    beginning += f'{f"-tune:v {settings.tune}" if settings.tune else ""} {generate_color_details(fastflix)} '

    if settings.profile and settings.profile != "default":
        beginning += f"-profile:v {settings.profile} "

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    if settings.bitrate:
        if settings.bitrate_passes == 2:
            command_1 = (
                f"{beginning} -pass 1 "
                f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra if settings.extra_both_passes else ""} -an -sn -dn {output_fps} -f mp4 {null}'
            )
            command_2 = (
                f'{beginning} -pass 2 -passlogfile "{pass_log_file}" '
                f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} "
            ) + ending
            return [
                Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
                Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
            ]
        else:
            command = f"{beginning} -b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} {ending}"
            return [Command(command=command, name="Single pass bitrate", exe="ffmpeg")]

    elif settings.crf:
        command = f"{beginning} -crf:v {settings.crf} " f"-preset:v {settings.preset} {settings.extra} {ending}"
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
