# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import x264Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: x264Settings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libx264")

    if settings.tune:
        beginning.extend(["-tune:v", settings.tune])

    beginning.extend(generate_color_details(fastflix))

    if settings.profile and settings.profile != "default":
        beginning.extend(["-profile:v", settings.profile])

    pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        if settings.bitrate_passes == 2:
            command_1 = (
                beginning
                + [
                    "-pass",
                    "1",
                    "-passlogfile",
                    str(pass_log_file),
                    "-b:v",
                    settings.bitrate,
                    "-preset:v",
                    settings.preset,
                ]
                + extra_both
                + ["-an", "-sn", "-dn"]
                + output_fps
                + ["-f", "mp4", null]
            )
            command_2 = (
                beginning
                + [
                    "-pass",
                    "2",
                    "-passlogfile",
                    str(pass_log_file),
                    "-b:v",
                    settings.bitrate,
                    "-preset:v",
                    settings.preset,
                ]
                + extra
                + ending
            )
            return [
                Command(command=command_1, name="First pass bitrate", exe="ffmpeg"),
                Command(command=command_2, name="Second pass bitrate", exe="ffmpeg"),
            ]
        else:
            command = beginning + ["-b:v", settings.bitrate, "-preset:v", settings.preset] + extra + ending
            return [Command(command=command, name="Single pass bitrate", exe="ffmpeg")]

    elif settings.crf:
        command = beginning + ["-crf:v", str(settings.crf), "-preset:v", settings.preset] + extra + ending
        return [Command(command=command, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
