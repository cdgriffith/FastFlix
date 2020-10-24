# -*- coding: utf-8 -*-
import secrets
from pathlib import Path

from fastflix.encoders.common.helpers import Command, generate_filters, generate_ffmpeg_start, generate_ending

extension = "gif"


def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    output_video,
    lossless=True,
    compression=6,
    extra="",
    preset="default",
    start_time=0,
    qscale="75",
    **kwargs,
):
    filters = generate_filters(video_track=video_track, **kwargs)
    beginning = generate_ffmpeg_start(
        source, ffmpeg, encoder="libwebp", video_track=video_track, start_time=start_time, filters=filters, **kwargs
    )
    ending = generate_ending("", "", "", output_video=output_video, **kwargs)

    return [
        Command(
            f"{beginning}  -lossless {lossless} -compression_level {compression} "
            f"-qscale {qscale} -preset {preset} {extra} {ending}",
            ["ffmpeg", "output"],
            False,
            name="WebP",
            exe="ffmpeg",
        ),
    ]
