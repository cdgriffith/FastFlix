# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import VP9Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: VP9Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libvpx-vp9")

    if settings.row_mt:
        beginning.extend(["-row-mt", "1"])
    beginning.extend(generate_color_details(fastflix))

    if not settings.single_pass:
        pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
        beginning.extend(["-passlogfile", str(pass_log_file)])

    # TODO color_range 1
    # if not fastflix.current_video.video_settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
    #     if fastflix.current_video.color_space.startswith("bt2020"):
    #         beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -color_range 1"

    if settings.auto_alt_ref >= 0:
        beginning.extend(["-auto-alt-ref", str(settings.auto_alt_ref)])

    if settings.lag_in_frames >= 0:
        beginning.extend(["-lag-in-frames", str(settings.lag_in_frames)])

    if settings.tune_content != "default":
        beginning.extend(["-tune-content", settings.tune_content])

    if settings.aq_mode >= 0:
        beginning.extend(["-aq-mode", str(settings.aq_mode)])

    if settings.sharpness >= 0:
        beginning.extend(["-sharpness", str(settings.sharpness)])

    details = [
        "-quality:v",
        settings.quality,
        "-profile:v",
        str(settings.profile),
        "-tile-columns:v",
        str(settings.tile_columns),
        "-tile-rows:v",
        str(settings.tile_rows),
    ]

    extra = shlex.split(settings.extra) if settings.extra else []
    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []

    if settings.bitrate:
        if settings.quality == "realtime":
            return [
                Command(
                    command=(
                        beginning
                        + ["-speed:v", str(settings.speed), "-b:v", settings.bitrate]
                        + details
                        + extra
                        + ending
                    ),
                    name="Single pass realtime bitrate",
                    exe="ffmpeg",
                )
            ]
        command_1 = (
            beginning
            + ["-speed:v", str("4" if settings.fast_first_pass else settings.speed), "-b:v", settings.bitrate]
            + details
            + ["-pass", "1"]
            + extra_both
            + ["-an"]
            + output_fps
            + ["-f", "webm", null]
        )
        command_2 = (
            beginning
            + ["-speed:v", str(settings.speed), "-b:v", settings.bitrate]
            + details
            + ["-pass", "2"]
            + extra
            + ending
        )

    elif settings.crf:
        command_1 = (
            beginning
            + ["-b:v", "0", "-crf:v", str(settings.crf)]
            + details
            + ["-pass", "1"]
            + extra_both
            + ["-an"]
            + output_fps
            + ["-f", "webm", null]
        )
        command_2 = (
            beginning
            + ["-b:v", "0", "-crf:v", str(settings.crf)]
            + details
            + (["-pass", "2"] if not settings.single_pass else [])
            + extra
            + ending
        )

    else:
        return []

    if settings.crf and settings.single_pass:
        return [Command(command=command_2, name="Single pass CRF", exe="ffmpeg")]
    pass_type = "bitrate" if settings.bitrate else "CRF"

    return [
        Command(command=command_1, name=f"First pass {pass_type}", exe="ffmpeg"),
        Command(command=command_2, name=f"Second pass {pass_type} ", exe="ffmpeg"),
    ]
