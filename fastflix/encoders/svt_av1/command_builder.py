#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import secrets

import reusables

from fastflix.encoders.common.helpers import Command, generate_all, null, generate_color_details
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


@reusables.log_exception("fastflix", show_traceback=True)
def build(fastflix: FastFlix):
    settings: SVTAV1Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending = generate_all(fastflix, "libsvtav1")

    beginning += (
        f"-strict experimental "
        f"-preset {settings.speed} "
        f"-tile_columns {settings.tile_columns} "
        f"-tile_rows {settings.tile_rows} "
        f"-tier {settings.tier} "
        f"{generate_color_details(fastflix)} "
    )

    beginning = re.sub("[ ]+", " ", beginning)

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    pass_type = "bitrate" if settings.bitrate else "QP"

    if settings.single_pass:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} -rc 1 {settings.extra} {ending}"

        elif settings.qp is not None:
            command_1 = f"{beginning} -qp {settings.qp} -rc 0 {settings.extra} {ending}"
        else:
            return []
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} -rc 1 -pass 1 {settings.extra if settings.extra_both_passes else ''} -an -f matroska {null}"
            command_2 = f"{beginning} -b:v {settings.bitrate} -rc 1 -pass 2 {settings.extra} {ending}"

        elif settings.qp is not None:
            command_1 = f"{beginning} -qp {settings.qp} -rc 0 -pass 1 {settings.extra if settings.extra_both_passes else ''} -an -f matroska {null}"
            command_2 = f"{beginning} -qp {settings.qp} -rc 0 -pass 2 {settings.extra} {ending}"
        else:
            return []
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
