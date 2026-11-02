# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details
from fastflix.models.encode import H264VideoToolboxSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: H264VideoToolboxSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "h264_videotoolbox")

    beginning.extend(generate_color_details(fastflix))

    h264_profiles = {1: "baseline", 2: "main", 3: "high", 4: "extended"}

    def clean_bool(item):
        return "true" if item else "false"

    details = []
    profile_name = h264_profiles.get(settings.profile)
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
