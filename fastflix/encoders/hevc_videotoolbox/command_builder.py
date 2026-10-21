# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, hevc_tag_args
from fastflix.models.encode import HEVCVideoToolboxSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: HEVCVideoToolboxSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "hevc_videotoolbox")

    beginning.extend(generate_color_details(fastflix))
    beginning.extend(hevc_tag_args(fastflix.current_video.video_settings.output_path))

    hevc_profiles = {1: "main", 2: "main10"}
    ten_bit_pix_fmts = ("p010le", "yuv420p10le")

    def clean_bool(item):
        return "true" if item else "false"

    details = []
    profile_name = hevc_profiles.get(settings.profile)
    if profile_name:
        profile_name = "main10" if settings.pix_fmt in ten_bit_pix_fmts else "main"
    if profile_name:
        details.extend(["-profile:v", profile_name])
    details.extend(
        [
            "-allow_sw",
            clean_bool(settings.allow_sw),
            "-require_sw",
            clean_bool(settings.require_sw),
            "-realtime",
            clean_bool(settings.realtime),
            "-frames_before",
            clean_bool(settings.frames_before),
            "-frames_after",
            clean_bool(settings.frames_after),
        ]
    )

    extra = shlex.split(settings.extra) if settings.extra else []

    if settings.bitrate:
        bitrate_args = ["-b:v", settings.bitrate]
        if settings.constant_bit_rate:
            bitrate_args.extend(["-constant_bit_rate", "true"])
        command = beginning + bitrate_args + details + extra + ending
        return [Command(command=command, name="Single pass bitrate", exe="ffmpeg")]
    command = beginning + ["-q:v", str(settings.q)] + details + extra + ending

    return [
        Command(command=command, name="Single pass constant quality", exe="ffmpeg"),
    ]
