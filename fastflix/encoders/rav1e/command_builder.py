#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import rav1eSettings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    settings: rav1eSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "librav1e")

    beginning.extend(
        [
            "-strict",
            "experimental",
            "-speed",
            str(settings.speed),
            "-tile-columns",
            str(settings.tile_columns),
            "-tile-rows",
            str(settings.tile_rows),
            "-tiles",
            str(settings.tiles),
        ]
    )
    beginning.extend(generate_color_details(fastflix))

    # Currently unsupported https://github.com/xiph/rav1e/issues/2554
    #         rav1e_options = []
    # if side_data.master_display:
    #     rav1e_options.append(
    #         "mastering-display="
    #         f"G{side_data.master_display.green}"
    #         f"B{side_data.master_display.blue}"
    #         f"R{side_data.master_display.red}"
    #         f"WP{side_data.master_display.white}"
    #         f"L{side_data.master_display.luminance}"
    #     )
    #
    # if side_data.cll:
    #     rav1e_options.append(f"content-light={side_data.cll}")
    # if rav1e_options:
    #     opts = ":".join(rav1e_options)
    #     beginning += f'-rav1e-params "{opts}"'

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        beginning.extend(["-passlogfile", str(pass_log_file)])

    pass_type = "bitrate" if settings.bitrate else "QP"

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if not settings.bitrate:
        command_1 = beginning + ["-qp", str(settings.qp)] + extra + ending
        return [Command(command=command_1, name=f"{pass_type}", exe="ffmpeg")]

    if settings.single_pass:
        command_1 = beginning + ["-b:v", settings.bitrate] + extra + ending
        return [Command(command=command_1, name=f"{pass_type}", exe="ffmpeg")]
    else:
        command_1 = (
            beginning
            + ["-b:v", settings.bitrate, "-pass", "1"]
            + extra_both
            + ["-an"]
            + output_fps
            + ["-f", "matroska", null]
        )
        command_2 = beginning + ["-b:v", settings.bitrate, "-pass", "2"] + extra + ending
        return [
            Command(command=command_1, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command=command_2, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
