#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import secrets

import reusables

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import SVTAVIFSettings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


@reusables.log_exception("fastflix", show_traceback=True)
def build(fastflix: FastFlix):
    settings: SVTAVIFSettings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libsvtav1", audio=False)

    beginning += f"-strict experimental " f"-preset {settings.speed} " f"{generate_color_details(fastflix)} "

    svtav1_params = settings.svtav1_params.copy()

    if not fastflix.current_video.video_settings.remove_hdr:
        if (
            fastflix.current_video.video_settings.color_primaries == "bt2020"
            or fastflix.current_video.color_primaries == "bt2020"
        ):
            svtav1_params.append(f"color-primaries=9")

        if (
            fastflix.current_video.video_settings.color_transfer == "smpte2084"
            or fastflix.current_video.color_transfer == "smpte2084"
        ):
            svtav1_params.append(f"transfer-characteristics=16")

        if (
            fastflix.current_video.video_settings.color_space
            and "bt2020" in fastflix.current_video.video_settings.color_space
        ) or (fastflix.current_video.color_space and "bt2020" in fastflix.current_video.color_space):
            svtav1_params.append(f"matrix-coefficients=9")

        enable_hdr = False
        if settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):

            def convert_me(two_numbers, conversion_rate=50_000) -> str:
                num_one, num_two = map(int, two_numbers.strip("()").split(","))
                return f"{num_one / conversion_rate:0.4f},{num_two / conversion_rate:0.4f}"

            if fastflix.current_video.master_display:
                svtav1_params.append(
                    "mastering-display="
                    f"G({convert_me(fastflix.current_video.master_display.green)})"
                    f"B({convert_me(fastflix.current_video.master_display.blue)})"
                    f"R({convert_me(fastflix.current_video.master_display.red)})"
                    f"WP({convert_me(fastflix.current_video.master_display.white)})"
                    f"L({convert_me(fastflix.current_video.master_display.luminance, 10_000)})"
                )
                enable_hdr = True

            if fastflix.current_video.cll:
                svtav1_params.append(f"content-light={fastflix.current_video.cll}")
                enable_hdr = True

            if enable_hdr:
                svtav1_params.append("enable-hdr=1")

    if svtav1_params:
        beginning += f" -svtav1-params \"{':'.join(svtav1_params)}\" "

    pass_type = "bitrate" if settings.bitrate else "QP"

    if settings.bitrate:
        command_1 = f"{beginning} -b:v {settings.bitrate} {settings.extra} -f avif {ending}"

    elif settings.qp is not None:
        command_1 = f"{beginning} -{settings.qp_mode} {settings.qp} {settings.extra} -f avif {ending}"
    else:
        return []
    return [Command(command=command_1, name=f"{pass_type}", exe="ffmpeg")]
