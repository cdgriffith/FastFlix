# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details
from fastflix.models.encode import FFmpegAV1NVENCSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: FFmpegAV1NVENCSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(
        fastflix, "av1_nvenc", start_extra="-hwaccel auto" if settings.hw_accel else ""
    )

    if settings.tune:
        beginning.extend(["-tune:v", settings.tune])
    beginning.extend(generate_color_details(fastflix))
    beginning.extend(
        [
            "-spatial-aq:v",
            str(settings.spatial_aq),
            "-temporal-aq:v",
            str(settings.temporal_aq),
            "-tier:v",
            str(settings.tier),
            "-rc-lookahead:v",
            str(settings.rc_lookahead),
            "-gpu",
            str(settings.gpu),
            "-b_ref_mode",
            str(settings.b_ref_mode),
        ]
    )

    if settings.multipass != "disabled":
        beginning.extend(["-multipass:v", settings.multipass])

    if settings.rc:
        beginning.extend(["-rc:v", settings.rc])

    if settings.level:
        beginning.extend(["-level:v", settings.level])

    if settings.aq_strength != 8:
        beginning.extend(["-aq-strength:v", str(settings.aq_strength)])

    extra = shlex.split(settings.extra) if settings.extra else []

    if not settings.bitrate:
        command = beginning + ["-qp:v", str(settings.qp), "-preset:v", settings.preset] + extra + ending
        return [Command(command=command, name="Single QP encode", exe="ffmpeg")]

    # NVENC performs two-pass internally via -multipass; FFmpeg's -pass/-2pass are not supported by NVENC
    command = beginning + ["-b:v", settings.bitrate, "-preset:v", settings.preset] + extra + ending
    return [Command(command=command, name="Bitrate encode", exe="ffmpeg")]
