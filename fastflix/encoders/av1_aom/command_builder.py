# -*- coding: utf-8 -*-
import logging
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import AOMAV1Settings
from fastflix.models.fastflix import FastFlix

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    settings: AOMAV1Settings = fastflix.current_video.video_settings.video_encoder_settings
    beginning, ending, output_fps = generate_all(fastflix, "libaom-av1")

    if fastflix.current_video.hdr10_plus and "10" in settings.pix_fmt:
        if fastflix.libavcodec_version >= 62:
            logger.info("HDR10+ detected — passthrough will be handled automatically by FFmpeg 8.0+")
        else:
            logger.warning(
                "HDR10+ detected but FFmpeg 8.0+ (libavcodec 62+) is required for AV1 HDR10+ passthrough. "
                f"Current libavcodec version: {fastflix.libavcodec_version}"
            )

    beginning.extend(
        [
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

    if settings.tune != "default":
        beginning.extend(["-tune", settings.tune])

    if settings.denoise_noise_level > 0:
        beginning.extend(["-denoise-noise-level", str(settings.denoise_noise_level)])

    if settings.aq_mode != "default":
        beginning.extend(["-aq-mode", settings.aq_mode])

    if settings.aom_params:
        beginning.extend(["-aom-params", ":".join(settings.aom_params)])

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
        command_1 = beginning + ["-crf", str(settings.crf)] + extra + ending
        return [Command(command=command_1, name="Single Pass CRF")]
