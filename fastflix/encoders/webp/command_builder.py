# -*- coding: utf-8 -*-
from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix
from fastflix.models.encode import WebPSettings


def build(fastflix: FastFlix):
    settings: WebPSettings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending = generate_all(fastflix, "libwebp", audio=False, subs=False)

    return [
        Command(
            f"{beginning}  -lossless {settings.lossless} -compression_level {settings.compression} "
            f"-qscale {settings.qscale} -preset {settings.preset} {settings.extra} {ending}",
            ["ffmpeg", "output"],
            False,
            name="WebP",
            exe="ffmpeg",
        ),
    ]
