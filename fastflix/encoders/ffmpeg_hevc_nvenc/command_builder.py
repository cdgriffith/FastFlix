# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, hevc_tag_args
from fastflix.encoders.common.nvenc_options import advanced_args, uses_cq
from fastflix.models.encode import FFmpegNVENCSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: FFmpegNVENCSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(
        fastflix, "hevc_nvenc", start_extra="-hwaccel auto" if settings.hw_accel else ""
    )

    if settings.tune:
        beginning.extend(["-tune:v", settings.tune])
    beginning.extend(generate_color_details(fastflix))
    beginning.extend(
        [
            "-spatial-aq:v",
            str(settings.spatial_aq),
            "-tier:v",
            settings.tier,
            "-rc-lookahead:v",
            str(settings.rc_lookahead),
            "-gpu",
            str(settings.gpu),
            "-b_ref_mode",
            str(settings.b_ref_mode),
        ]
    )
    if settings.temporal_aq:
        beginning.extend(["-temporal-aq:v", str(settings.temporal_aq)])
    if settings.aq_strength != 8:
        beginning.extend(["-aq-strength:v", str(settings.aq_strength)])
    beginning.extend(advanced_args(settings))
    beginning.extend(hevc_tag_args(fastflix.current_video.video_settings.output_path))

    if settings.profile:
        beginning.extend(["-profile:v", settings.profile])

    cq_mode = uses_cq(settings)
    if settings.rc:
        beginning.extend(["-rc:v", settings.rc])
    elif cq_mode:
        beginning.extend(["-rc:v", "vbr"])

    if settings.level:
        beginning.extend(["-level:v", settings.level])

    extra = shlex.split(settings.extra) if settings.extra else []

    if cq_mode:
        quality = ["-cq:v", str(settings.cq), "-b:v", "0"]
        command = beginning + quality + ["-preset:v", settings.preset] + extra + ending
        return [Command(command=command, name="Constant quality encode", exe="ffmpeg")]

    if not settings.bitrate:
        command = beginning + ["-qp:v", str(settings.qp), "-preset:v", settings.preset] + extra + ending
        return [Command(command=command, name="Single QP encode", exe="ffmpeg")]

    # NVENC performs two-pass internally via -multipass; FFmpeg's -pass/-2pass are not supported by NVENC
    multipass = ["-multipass:v", settings.multipass] if settings.multipass != "disabled" else []
    command = beginning + ["-b:v", settings.bitrate, "-preset:v", settings.preset] + multipass + extra + ending
    return [Command(command=command, name="Bitrate encode", exe="ffmpeg")]
