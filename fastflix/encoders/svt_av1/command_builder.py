#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import secrets
from pathlib import Path

import reusables

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


@reusables.log_exception("fastflix", show_traceback=True)
def build(fastflix: FastFlix):
    settings: SVTAV1Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending = generate_all(fastflix, "libsvtav1")

    if not fastflix.current_video.video_settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):

        if fastflix.current_video.color_space.startswith("bt2020"):
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

    beginning = re.sub("[ ]+", " ", beginning)

    if not settings.single_pass:
        pass_log_file = Path(fastflix.current_video.work_path.name) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    pass_type = "bitrate" if settings.bitrate else "QP"

    if settings.single_pass:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} -rc 1" + ending

        elif settings.qp is not None:
            command_1 = f"{beginning} -qp {settings.qp} -rc 0" + ending
        else:
            return []
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} -rc 1 -pass 1 -an -f matroska {null}"
            command_2 = f"{beginning} -b:v {settings.bitrate} -rc 1 -pass 2" + ending

        elif settings.qp is not None:
            command_1 = f"{beginning} -qp {settings.qp} -rc 0 -pass 1 -an -f matroska {null}"
            command_2 = f"{beginning} -qp {settings.qp} -rc 0 -pass 2" + ending
        else:
            return []
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
