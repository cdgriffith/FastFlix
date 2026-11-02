#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details
from fastflix.encoders.common.vaapi import vaapi_rate_control_args, vaapi_sw_format
from fastflix.models.encode import VAAPIVP9Settings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    settings: VAAPIVP9Settings = fastflix.current_video.video_settings.video_encoder_settings
    # Frames are decoded (hardware when possible, otherwise software) into system memory, filtered in software and
    # uploaded with hwupload, so a source the GPU cannot decode still works.
    start_extra = [
        "-init_hw_device",
        f"vaapi=hwdev:{settings.vaapi_device}",
        "-hwaccel",
        "vaapi",
        "-hwaccel_device",
        "hwdev",
    ]
    beginning, ending, output_fps = generate_all(
        fastflix,
        "vp9_vaapi",
        start_extra=start_extra,
        enable_opencl=False,
        vaapi=True,
        vaapi_format=vaapi_sw_format(settings.bit_depth),
    )

    beginning.extend(
        [
            "-b_depth",
            str(settings.b_depth),
            "-idr_interval",
            str(settings.idr_interval),
        ]
    )
    beginning.extend(generate_color_details(fastflix))
    beginning.extend(["-filter_hw_device", "hwdev"])

    if settings.low_power:
        beginning.extend(["-low_power", "1"])

    beginning.extend(["-profile:v", "2" if vaapi_sw_format(settings.bit_depth) == "p010le" else "0"])

    rate_control = vaapi_rate_control_args(settings, explicit_qp=False)
    pass_type = "bitrate" if settings.bitrate else "QP"

    command_1 = beginning + rate_control + (shlex.split(settings.extra) if settings.extra else []) + ending
    return [Command(command=command_1, name=f"{pass_type}", exe="ffmpeg")]
