# -*- coding: utf-8 -*-
from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.encode import WebPSettings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: WebPSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending, output_fps = generate_all(fastflix, "libwebp", audio=False, subs=False)

    return [
        Command(
            command=f"{beginning}  -lossless {'1' if settings.lossless.lower() in ('1', 'yes') else '0'} "
            f"-compression_level {settings.compression} "
            f"-qscale {settings.qscale} -preset {settings.preset} {settings.extra} {ending}",
            name="WebP",
            exe="ffmpeg",
        ),
    ]
