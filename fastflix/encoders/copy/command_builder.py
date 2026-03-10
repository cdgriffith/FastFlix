# -*- coding: utf-8 -*-
import shlex

from fastflix.encoders.common.helpers import Command, generate_all
from fastflix.models.fastflix import FastFlix

# Containers that support display matrix metadata (rotation/flip) without re-encoding
DISPLAY_MATRIX_CONTAINERS = {".mp4", ".mov", ".mkv", ".m4v"}


def build(fastflix: FastFlix):
    if not fastflix.current_video.current_video_stream:
        return []

    rotation = fastflix.current_video.source_rotation

    # Build display matrix input options (placed before -i via start_extra).
    # These use modern FFmpeg display matrix side data (requires FFmpeg 6.0+).
    display_args = []
    output_ext = fastflix.current_video.video_settings.output_path.suffix.lower()

    if output_ext in DISPLAY_MATRIX_CONTAINERS:
        desired_rotation = (rotation + (fastflix.current_video.video_settings.rotate * 90)) % 360
        display_args = ["-display_rotation:v:0", str(desired_rotation)]

        if fastflix.current_video.video_settings.horizontal_flip:
            display_args.extend(["-display_hflip:v:0", "1"])
        if fastflix.current_video.video_settings.vertical_flip:
            display_args.extend(["-display_vflip:v:0", "1"])

    beginning, ending, output_fps = generate_all(fastflix, "copy", disable_filters=True, start_extra=display_args)

    extra = (
        shlex.split(fastflix.current_video.video_settings.video_encoder_settings.extra)
        if fastflix.current_video.video_settings.video_encoder_settings.extra
        else []
    )

    return [
        Command(
            command=beginning + extra + ending,
            name="No Video Encoding",
            exe="ffmpeg",
        )
    ]
