#!/usr/bin/env python
# -*- coding: utf-8 -*-

import reusables

from pathlib import Path
import logging

from fastflix.plugins.common.helpers import generate_filters, Command
from fastflix.plugins.common.audio import build_audio

logger = logging.getLogger("fastflix")


class FlixError(Exception):
    pass


extension = "mkv"


@reusables.log_exception("fastflix", show_traceback=True)
def build(source, video_track, streams, start_time, format_info, duration, mode=7, qp=25, audio_tracks=(), **kwargs):
    file = Path(source)
    filters = generate_filters(**kwargs)

    fps_num, fps_denom = [
        int(x) for x in streams.video[0].get("avg_frame_rate", streams.video[0].r_frame_rate).split("/")
    ]
    bit_depth = 10 if streams.video[0].pix_fmt == "yuv420p10le" else 8
    crop = kwargs.get("crop")
    scale = kwargs.get("scale")

    if scale:
        width, height = (int(x) for x in scale.split(":"))
    else:
        height = int(streams.video[0].height)
        width = int(streams.video[0].width)
    assert height <= 2160
    assert width <= 4096

    if crop:
        crop_check = crop.split(":")
        try:
            assert crop_check[0] % 8 == 0
            assert crop_check[1] % 8 == 0
        except AssertionError:
            raise FlixError("CROP BAD: Video height and main_width must be divisible by 8")
    else:
        crop_height = height % 8
        crop_width = width % 8
        if crop_height or crop_width:
            raise FlixError("CROP BAD: Video height and main_width must be divisible by 8")

    intra_period = 1
    for i in range(1, 31):
        intra_period = (i * 8) - 1
        if (intra_period + 8) > (fps_num / fps_denom):
            break
    total_time = kwargs.get("duration", format_info.duration) - start_time
    frames = int(total_time * int(fps_num / fps_denom))
    command_1 = Command(
        (
            f'"{{ffmpeg}}" {f"-ss {start_time}" if start_time else ""} '
            f'-nostdin -i "{source}" -vframes {frames} -f rawvideo '
            f'{f"-vf {filters}" if filters else ""} '
            f'-pix_fmt {"yuv420p" if bit_depth == 8 else "yuv420p10le"} -an - | '
            f'"{{av1}}" -intra-period {intra_period} -enc-mode {mode} -w {width} -h {height} '
            f"-bit-depth {bit_depth} -n {frames} -i stdin -q {qp} "
            f"-fps-num {fps_num} -fps-denom {fps_denom} -b <tempfile.1.ivf>"
        ),
        ["ffmpeg", "av1"],
        False,
    )

    audio = build_audio(audio_tracks, audio_file_index=1)

    command_3 = Command(
        (
            f'"{{ffmpeg}}" -y '
            f'{f"-ss {start_time}" if start_time else ""} '
            f'{f"-t {duration - start_time}" if duration else ""} '
            f'-i "<tempfile.1.ivf>" -i "{file}" '
            f"-c copy -map 0:{video_track} "  # -af "aresample=async=1:min_hard_comp=0.100000:first_pts=0"
            f'{audio} "{{output}}"'
        ),
        ["ffmpeg", "output"],
        False,
    )

    return command_1, command_3
