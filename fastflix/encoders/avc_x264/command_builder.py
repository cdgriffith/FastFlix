# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path

import reusables
from box import Box

from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.helpers import Command, generate_filters
from fastflix.encoders.common.subtitles import build_subtitle


def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    bitrate=None,
    crf=None,
    start_time=0,
    duration=None,
    preset="fast",
    audio_tracks=(),
    subtitle_tracks=(),
    disable_hdr=False,
    side_data=None,
    max_mux="default",
    extra="",
    pix_fmt="yuv420p10le",
    tune=None,
    profile="default",
    attachments="",
    **kwargs,
):
    filters = generate_filters(disable_hdr=disable_hdr, **kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)

    ending = "/dev/null"
    if reusables.win_based:
        ending = "NUL"

    if not side_data:
        side_data = Box(default_box=True)

    beginning = (
        f'"{ffmpeg}" -y '
        f'-i "{source}" '
        f' {f"-ss {start_time}" if start_time else ""}  '
        f'{f"-to {duration}" if duration else ""} '
        f"{extra} "
        f"-map 0:{video_track} "
        f"-pix_fmt {pix_fmt} "
        f"-c:v:0 libx264 "
        f'{f"-vf {filters}" if filters else ""} '
        f'{f"-tune {tune}" if tune else ""} '
        "-map_metadata -1 "
        f"{attachments} "
    )

    if profile and profile != "default":
        beginning += f"-profile {profile} "

    if max_mux and max_mux != "default":
        beginning += f"-max_muxing_queue_size {max_mux} "

    if side_data.cll:
        pass

    extra_data = "-map_chapters 0 "  # -map_metadata 0 # safe to do for rotation?
    pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"

    if bitrate:
        command_1 = (
            f"{beginning} -pass 1 "
            f'-passlogfile "{pass_log_file}" -b:v {bitrate} -preset {preset} -an -sn -dn -f mp4 {ending}'
        )
        command_2 = (
            f'{beginning} -pass 2 -passlogfile "{pass_log_file}" '
            f'-b:v {bitrate} -preset {preset} {audio} {subtitles} {extra_data} "{{output}}"'
        )
        return [
            Command(
                re.sub("[ ]+", " ", command_1), ["ffmpeg", "output"], False, name="First pass bitrate", exe="ffmpeg"
            ),
            Command(
                re.sub("[ ]+", " ", command_2), ["ffmpeg", "output"], False, name="Second pass bitrate", exe="ffmpeg"
            ),
        ]

    elif crf:
        command = f"{beginning} -crf {crf} " f'-preset {preset} {audio} {subtitles} {extra_data} "{{output}}"'
        return [
            Command(re.sub("[ ]+", " ", command), ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")
        ]

    else:
        return []
