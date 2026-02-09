# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import HEVCVideoToolboxSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: HEVCVideoToolboxSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "hevc_videotoolbox")

    beginning.extend(generate_color_details(fastflix))

    def clean_bool(item):
        return "true" if item else "false"

    details = [
        "-profile:v",
        str(settings.profile),
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

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

        command_1 = (
            beginning
            + ["-b:v", settings.bitrate]
            + details
            + ["-pass", "1", "-passlogfile", str(pass_log_file)]
            + extra_both
            + ["-an"]
            + output_fps
            + ["-f", "mp4", null]
        )
        command_2 = (
            beginning
            + ["-b:v", settings.bitrate]
            + details
            + ["-pass", "2", "-passlogfile", str(pass_log_file)]
            + extra
            + ending
        )
        return [
            Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
        ]
    command_1 = beginning + ["-q:v", str(settings.q)] + details + extra + ending

    return [
        Command(command=command_1, name="Single pass constant quality", exe="ffmpeg"),
    ]
