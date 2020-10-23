# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path

from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.helpers import Command, generate_ending, generate_ffmpeg_start, generate_filters, null
from fastflix.encoders.common.subtitles import build_subtitle


def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    output_video,
    bitrate=None,
    crf=None,
    audio_tracks=(),
    subtitle_tracks=(),
    disable_hdr=False,
    side_data=None,
    row_mt=None,
    cpu_used="1",
    tile_columns="-1",
    tile_rows="-1",
    attachments="",
    pix_fmt="yuv420p10le",
    usage="good",
    **kwargs,
):
    audio = build_audio(audio_tracks)
    subtitles, burn_in_track = build_subtitle(subtitle_tracks)
    filters = generate_filters(video_track=video_track, disable_hdr=disable_hdr, burn_in_track=burn_in_track, **kwargs)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)
    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="libaom-av1",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += (
        "-strict experimental "
        f"-cpu-used {cpu_used} "
        f"-tile-rows {tile_rows} "
        f"-tile-columns {tile_columns} "
        f"-usage {usage} "
    )

    if row_mt is not None:
        beginning += f"-row-mt {row_mt} "

    if not disable_hdr and pix_fmt in ("yuv420p10le", "yuv420p12le"):

        if side_data and side_data.get("color_primaries") == "bt2020":
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

    beginning = re.sub("[ ]+", " ", beginning)

    if bitrate:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        command_1 = f'{beginning} -passlogfile "{pass_log_file}" -b:v {bitrate} -pass 1 -an -f matroska {null}'
        command_2 = f'{beginning} -passlogfile "{pass_log_file}" -b:v {bitrate} -pass 2' + ending
        return [
            Command(command_1, ["ffmpeg", "output"], False, name="First Pass bitrate"),
            Command(command_2, ["ffmpeg", "output"], False, name="Second Pass bitrate"),
        ]
    elif crf:
        command_1 = f"{beginning} -b:v 0 -crf {crf}" + ending
        return [Command(command_1, ["ffmpeg", "output"], False, name="Single Pass CRF")]
