#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import secrets
from pathlib import Path

import reusables

from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.helpers import Command, generate_filters, start_and_input
from fastflix.encoders.common.subtitles import build_subtitle

logger = logging.getLogger("fastflix")


class FlixError(Exception):
    pass


extension = "mkv"

ending = "/dev/null"
if reusables.win_based:
    ending = "NUL"


@reusables.log_exception("fastflix", show_traceback=True)
def build(
    source,
    video_track,
    stream_track,
    ffmpeg,
    streams,
    temp_dir,
    output_video,
    tier="main",
    tile_columns=0,
    tile_rows=0,
    speed=7,
    qp=25,
    sc_detection=0,
    pix_fmt="yuv420p10le",
    bitrate=None,
    audio_tracks=(),
    subtitle_tracks=(),
    single_pass=False,
    attachments="",
    extra="",
    **kwargs,
):
    filters = generate_filters(**kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)

    crop = kwargs.get("crop")
    scale = kwargs.get("scale")

    if scale:
        width, height = (int(x) for x in scale.split(":"))
    else:
        height = int(streams.video[stream_track].height)
        width = int(streams.video[stream_track].width)
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

    beginning = start_and_input(source, ffmpeg, **kwargs) + (
        f"{extra} "
        f"-map 0:{video_track} "
        f"-pix_fmt {pix_fmt} "
        f"-c:v:0 libsvtav1 -strict experimental "
        f"-preset {speed} "
        f"-tile_columns {tile_columns} "
        f"-tile_rows {tile_rows} "
        f"-tier {tier} "
        f"-sc_detection {sc_detection} "
        f'{f"-vf {filters}" if filters else ""} '
    )

    if not single_pass:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    beginning = re.sub("[ ]+", " ", beginning)

    pass_type = "bitrate" if bitrate else "QP"

    if single_pass:
        if bitrate:
            command_1 = f'{beginning} -b:v {bitrate} -rc 1 {audio} {subtitles} {attachments} "{output_video}"'

        elif qp is not None:
            command_1 = f'{beginning} -qp {qp} -rc 0 {audio} {subtitles} {attachments} "{output_video}"'
        else:
            return []
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        if bitrate:
            command_1 = f"{beginning} -b:v {bitrate} -rc 1 -pass 1 -an -f matroska {ending}"
            command_2 = f'{beginning} -b:v {bitrate} -rc 1 -pass 2 {audio} {subtitles} {attachments} "{output_video}"'

        elif qp is not None:
            command_1 = f"{beginning} -qp {qp} -rc 0 -pass 1 -an -f matroska {ending}"
            command_2 = f'{beginning} -qp {qp} -rc 0 -pass 2 {audio} {subtitles} {attachments} "{output_video}"'
        else:
            return []
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
