#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import secrets
from pathlib import Path

import reusables

from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.helpers import Command, generate_ending, generate_ffmpeg_start, generate_filters, null
from fastflix.encoders.common.subtitles import build_subtitle

logger = logging.getLogger("fastflix")


class FlixError(Exception):
    pass


extension = "mkv"


@reusables.log_exception("fastflix", show_traceback=True)
def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    output_video,
    tier="main",
    tile_columns=0,
    tile_rows=0,
    speed=7,
    qp=25,
    sc_detection=0,
    disable_hdr=False,
    pix_fmt="yuv420p10le",
    bitrate=None,
    audio_tracks=(),
    subtitle_tracks=(),
    side_data=None,
    single_pass=False,
    attachments="",
    **kwargs,
):
    filters = generate_filters(disable_hdr=disable_hdr, **kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)

    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="libsvtav1",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += (
        f"-strict experimental "
        f"-preset {speed} "
        f"-tile_columns {tile_columns} "
        f"-tile_rows {tile_rows} "
        f"-tier {tier} "
        f"-sc_detection {sc_detection} "
    )

    if not single_pass:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    if not disable_hdr and pix_fmt == "yuv420p10le":

        if side_data and side_data.get("color_primaries") == "bt2020":
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

    beginning = re.sub("[ ]+", " ", beginning)

    pass_type = "bitrate" if bitrate else "QP"

    if single_pass:
        if bitrate:
            command_1 = f"{beginning} -b:v {bitrate} -rc 1" + ending

        elif qp is not None:
            command_1 = f"{beginning} -qp {qp} -rc 0" + ending
        else:
            return []
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        if bitrate:
            command_1 = f"{beginning} -b:v {bitrate} -rc 1 -pass 1 -an -f matroska {null}"
            command_2 = f"{beginning} -b:v {bitrate} -rc 1 -pass 2" + ending

        elif qp is not None:
            command_1 = f"{beginning} -qp {qp} -rc 0 -pass 1 -an -f matroska {null}"
            command_2 = f"{beginning} -qp {qp} -rc 0 -pass 2" + ending
        else:
            return []
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
