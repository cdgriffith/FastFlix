#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import secrets

import reusables

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


@reusables.log_exception("fastflix", show_traceback=True)
def build(fastflix: FastFlix):
    settings: SVTAV1Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libsvtav1")

    beginning += f"-strict experimental " f"-preset {settings.speed} " f"{generate_color_details(fastflix)} "

    svtav1_params = settings.svtav1_params.copy()
    svtav1_params.extend(
        [
            f"tile-columns={settings.tile_columns}",
            f"tile-rows={settings.tile_rows}",
            f"scd={1 if settings.scene_detection else 0}",
        ]
    )

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

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        beginning += f'-passlogfile "{pass_log_file}" '

    pass_type = "bitrate" if settings.bitrate else "QP"

    if settings.single_pass:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} {settings.extra} {ending}"

        elif settings.qp is not None:
            command_1 = f"{beginning} -{settings.qp_mode} {settings.qp} {settings.extra} {ending}"
        else:
            return []
        return [Command(command=command_1, name=f"{pass_type}", exe="ffmpeg")]
    else:
        if settings.bitrate:
            command_1 = f"{beginning} -b:v {settings.bitrate} -pass 1 {settings.extra if settings.extra_both_passes else ''} -an {output_fps} -f matroska {null}"
            command_2 = f"{beginning} -b:v {settings.bitrate} -pass 2 {settings.extra} {ending}"

        elif settings.qp is not None:
            command_1 = f"{beginning} -{settings.qp_mode} {settings.qp} -pass 1 {settings.extra if settings.extra_both_passes else ''} -an {output_fps} -f matroska {null}"
            command_2 = f"{beginning} -{settings.qp_mode} {settings.qp} -pass 2 {settings.extra} {ending}"
        else:
            return []
        return [
            Command(command=command_1, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command=command_2, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
