# -*- coding: utf-8 -*-
import reusables
import re
from pathlib import Path
import secrets

from fastflix.encoders.common import helpers
from fastflix.encoders.common.audio import build_audio


def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    bitrate=None,
    crf=None,
    start_time=0,
    duration=None,
    audio_tracks=(),
    row_mt=None,
    cpu_used="1",
    tile_columns="-1",
    tile_rows="-1",
    **kwargs,
):
    filters = helpers.generate_filters(**kwargs)
    audio = build_audio(audio_tracks)

    ending = "/dev/null"
    if reusables.win_based:
        ending = "NUL"

    beginning = (
        f'"{ffmpeg}" -y '
        f' {f"-ss {start_time}" if start_time else ""}  '
        f'{f"-t {duration}" if duration else ""} '
        f'-i "{source}" '
        f"-map 0:{video_track} "
        f"-c:v:0 libaom-av1 -strict experimental "
        f'{f"-vf {filters}" if filters else ""} '
        f"-cpu-used {cpu_used} "
        f"-tile-rows {tile_rows} "
        f"-tile-columns {tile_columns} "
        "-map_metadata -1 "
    )

    if row_mt is not None:
        beginning += f"-row-mt {row_mt} "

    beginning = re.sub("[ ]+", " ", beginning)

    if bitrate:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        command_1 = f'{beginning} -passlogfile "{pass_log_file}" -b:v {bitrate} -pass 1 -an -f matroska {ending}'
        command_2 = f'{beginning} -passlogfile "{pass_log_file}" -b:v {bitrate} -pass 2 {audio} "{{output}}"'
        return [
            helpers.Command(command_1, ["ffmpeg", "output"], False, name="First Pass bitrate"),
            helpers.Command(command_2, ["ffmpeg", "output"], False, name="Second Pass bitrate"),
        ]
    elif crf:
        command_1 = f'{beginning} -b:v 0 -crf {crf} {audio} "{{output}}"'
        return [helpers.Command(command_1, ["ffmpeg", "output"], False, name="Single Pass CRF")]
