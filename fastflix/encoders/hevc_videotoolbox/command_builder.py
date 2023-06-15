# -*- coding: utf-8 -*-
import secrets

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import HEVCVideoToolboxSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: HEVCVideoToolboxSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "hevc_videotoolbox")

    beginning += generate_color_details(fastflix)

    def clean_bool(item):
        return "true" if item else "false"

    details = (
        f"-profile:v {settings.profile} "
        f"-allow_sw {clean_bool(settings.allow_sw)} "
        f"-require_sw {clean_bool(settings.require_sw)} "
        f"-realtime {clean_bool(settings.realtime)} "
        f"-frames_before {clean_bool(settings.frames_before)} "
        f"-frames_after {clean_bool(settings.frames_after)} "
    )

    if settings.bitrate:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        beginning += f" "

        command_1 = f"{beginning} -b:v {settings.bitrate} {details} -pass 1 -passlogfile \"{pass_log_file}\" {settings.extra if settings.extra_both_passes else ''} -an {output_fps} -f mp4 {null}"
        command_2 = f'{beginning} -b:v {settings.bitrate} {details} -pass 2 -passlogfile "{pass_log_file}" {settings.extra} {ending}'
        return [
            Command(command=command_1, name=f"First pass bitrate", exe="ffmpeg"),
            Command(command=command_2, name=f"Second pass bitrate", exe="ffmpeg"),
        ]
    command_1 = f"{beginning} -q:v {settings.q} {details} {settings.extra} {ending}"

    return [
        Command(command=command_1, name=f"Single pass constant quality", exe="ffmpeg"),
    ]
