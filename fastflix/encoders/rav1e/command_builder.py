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
    extra="",
    **kwargs,
):
    filters = generate_filters(disable_hdr=disable_hdr, **kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)

    beginning = start_and_input(source, ffmpeg, **kwargs) + (
        f"{extra}"
        f"-map 0:{video_track} "
        f"-pix_fmt {pix_fmt} "
        f"-c:v:0 librav1e -strict experimental "
        f"-speed {speed} "
        f"-tile-columns {tile_columns} "
        f"-tile-rows {tile_rows} "
        f"-tiles {tiles} "
        f'{f"-vf {filters}" if filters else ""} '
    )

    if not single_pass:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    if not disable_hdr and pix_fmt == "yuv420p10le":

        if side_data.color_primaries == "bt2020":
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
        command_1 = f'{beginning} -qp {qp} {audio} {subtitles} {attachments} "{output_video}"'
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]

    if single_pass:
        command_1 = f'{beginning} -b:v {bitrate} {audio} {subtitles} {attachments} "{output_video}"'
        return [Command(command_1, ["ffmpeg", "output"], False, name=f"{pass_type}", exe="ffmpeg")]
    else:
        command_1 = f"{beginning} -b:v {bitrate} -pass 1 -an -f matroska {ending}"
        command_2 = f'{beginning} -b:v {bitrate} -pass 2 {audio} {subtitles} {attachments} "{output_video}"'
        return [
            Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
        ]
