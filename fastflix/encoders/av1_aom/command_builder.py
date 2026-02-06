# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import AOMAV1Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: AOMAV1Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libaom-av1")

    beginning.extend(
        [
            "-strict",
            "experimental",
            "-cpu-used",
            str(settings.cpu_used),
            "-tile-rows",
            str(settings.tile_rows),
            "-tile-columns",
            str(settings.tile_columns),
            "-usage",
            settings.usage,
        ]
    )
    beginning.extend(generate_color_details(fastflix))

    if settings.row_mt.lower() == "enabled":
        beginning.extend(["-row-mt", "1"])

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        command_1 = (
            beginning
            + ["-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-pass", "1"]
            + extra_both
            + ["-an"]
            + output_fps
            + ["-f", "matroska", null]
        )
        command_2 = (
            beginning + ["-passlogfile", str(pass_log_file), "-b:v", settings.bitrate, "-pass", "2"] + extra + ending
        )
        return [
            Command(command=command_1, name="First Pass bitrate"),
            Command(command=command_2, name="Second Pass bitrate"),
        ]
    elif settings.crf:
        command_1 = beginning + ["-b:v", "0", "-crf", str(settings.crf)] + extra + ending
        return [Command(command=command_1, name="Single Pass CRF")]
