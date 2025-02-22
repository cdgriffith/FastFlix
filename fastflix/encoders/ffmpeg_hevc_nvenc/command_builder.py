# -*- coding: utf-8 -*-
import re
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import FFmpegNVENCSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: FFmpegNVENCSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(
        fastflix, "hevc_nvenc", start_extra="-hwaccel auto" if settings.hw_accel else ""
    )

    beginning += f'{f"-tune:v {settings.tune}" if settings.tune else ""} {generate_color_details(fastflix)} -spatial_aq:v {settings.spatial_aq} -tier:v {settings.tier} -rc-lookahead:v {settings.rc_lookahead} -gpu {settings.gpu} -b_ref_mode {settings.b_ref_mode} '

    if settings.profile:
        beginning += f"-profile:v {settings.profile} "

    if settings.rc:
        beginning += f"-rc:v {settings.rc} "

    if settings.level:
        beginning += f"-level:v {settings.level} "

    if not settings.bitrate:
        command = (f"{beginning} -qp:v {settings.qp} -preset:v {settings.preset} " f"{settings.extra}") + ending
        return [Command(command=command, name="Single QP encode", exe="ffmpeg")]

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    command_1 = (
        f"{beginning} -pass 1 "
        f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset:v {settings.preset} -2pass 1 '
        f'{settings.extra if settings.extra_both_passes else ""} -an -sn -dn {output_fps} -f mp4 {null}'
    )
    command_2 = (
        f'{beginning} -pass 2 -passlogfile "{pass_log_file}" -2pass 1 '
        f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} "
    ) + ending
    return [
        Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
        Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
    ]
