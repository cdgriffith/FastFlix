# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.encode import WebPSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: WebPSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libwebp", audio=False, subs=False)

    extra = shlex.split(settings.extra) if settings.extra else []

    command = (
        beginning
        + [
            "-lossless",
            "1" if settings.lossless.lower() in ("1", "yes") else "0",
            "-compression_level",
            str(settings.compression),
            "-qscale",
            str(settings.qscale),
            "-preset",
            settings.preset,
        ]
        + extra
        + ending
    )

    return [
        Command(
            command=command,
            name="WebP",
            exe="ffmpeg",
        ),
    ]
