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
    subtitle_tracks=(),
    single_pass=False,
    quality="good",
    audio_tracks=(),
    speed=1,
    row_mt=0,
    pix_fmt="yuv420p10le",
    attachments="",
    disable_hdr=False,
    side_data=None,
    **kwargs,
):
    audio = build_audio(audio_tracks)
    subtitles, burn_in_track = build_subtitle(subtitle_tracks)
    filters = generate_filters(video_track=video_track, disable_hdr=disable_hdr, burn_in_track=burn_in_track, **kwargs)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)
    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="libvpx-vp9",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += f'{"-row-mt 1" if row_mt else ""} '

    if not single_pass:
        pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"
        beginning += f'-passlogfile "{pass_log_file}" '

    if not disable_hdr and pix_fmt in ("yuv420p10le", "yuv420p12le"):

        if side_data and side_data.get("color_primaries") == "bt2020":
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

    beginning = re.sub("[ ]+", " ", beginning)

    if bitrate:
        command_1 = f"{beginning} -b:v {bitrate} -quality good -pass 1 -an -f webm {null}"
        command_2 = f"{beginning} -b:v {bitrate} -quality {quality} -speed {speed} -pass 2" + ending

    elif crf:
        command_1 = f"{beginning} -b:v 0 -crf {crf} -quality good -pass 1 -an -f webm {null}"
        command_2 = (
            f"{beginning} -b:v 0 -crf {crf} -quality {quality} -speed {speed} "
            f'{"-pass 2" if not single_pass else ""}'
        ) + ending

    else:
        return []

    if crf and single_pass:
        return [Command(command_2, ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")]
    pass_type = "bitrate" if bitrate else "CRF"
    return [
        Command(command_1, ["ffmpeg", "output"], False, name=f"First pass {pass_type}", exe="ffmpeg"),
        Command(command_2, ["ffmpeg", "output"], False, name=f"Second pass {pass_type} ", exe="ffmpeg"),
    ]
