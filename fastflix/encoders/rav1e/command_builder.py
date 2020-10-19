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
    tiles=0,
    tile_columns=0,
    tile_rows=0,
    speed=7,
    qp=-1,
    pix_fmt="yuv420p10le",
    bitrate=None,
    audio_tracks=(),
    subtitle_tracks=(),
    disable_hdr=False,
    side_data=None,
    single_pass=False,
    attachments="",
    **kwargs,
):
    audio = build_audio(audio_tracks)
    subtitles, burn_in_track = build_subtitle(subtitle_tracks)
    filters = generate_filters(video_track=video_track, disable_hdr=disable_hdr, burn_in_track=burn_in_track, **kwargs)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)

    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="librav1e",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += (
        "-strict experimental "
        f"-speed {speed} "
        f"-tile-columns {tile_columns} "
        f"-tile-rows {tile_rows} "
        f"-tiles {tiles} "
    )

    if not single_pass:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    if not disable_hdr and pix_fmt == "yuv420p10le":

        if side_data and side_data.get("color_primaries") == "bt2020":
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

        # Currently unsupported https://github.com/xiph/rav1e/issues/2554
        #         rav1e_options = []
        # if side_data.master_display:
        #     rav1e_options.append(
        #         "mastering-display="
        #         f"G{side_data.master_display.green}"
        #         f"B{side_data.master_display.blue}"
        #         f"R{side_data.master_display.red}"
        #         f"WP{side_data.master_display.white}"
        #         f"L{side_data.master_display.luminance}"
        #     )
        #
        # if side_data.cll:
        #     rav1e_options.append(f"content-light={side_data.cll}")
        # if rav1e_options:
        #     opts = ":".join(rav1e_options)
        #     beginning += f'-rav1e-params "{opts}"'

    beginning = re.sub("[ ]+", " ", beginning)

    pass_type = "bitrate" if bitrate else "QP"

    if not bitrate:
        command_1 = f"{beginning} -qp {qp}" + ending
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]

    if single_pass:
        command_1 = f'{beginning} -b:v {bitrate} {audio} {subtitles} {attachments} "{output_video}"'
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        command_1 = f"{beginning} -b:v {bitrate} -pass 1 -an -f matroska {null}"
        command_2 = f"{beginning} -b:v {bitrate} -pass 2" + ending
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
