# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path

from box import Box

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
    preset="fast",
    audio_tracks=(),
    subtitle_tracks=(),
    disable_hdr=False,
    side_data=None,
    pix_fmt="yuv420p",
    tune=None,
    profile="default",
    attachments="",
    **kwargs,
):
    filters = generate_filters(disable_hdr=disable_hdr, **kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)

    if not side_data:
        side_data = Box(default_box=True)

    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="libx264",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += f'{f"-tune {tune}" if tune else ""} '

    if profile and profile != "default":
        beginning += f"-profile {profile} "

    if not disable_hdr and pix_fmt == "yuv420p10le":

        if side_data and side_data.get("color_primaries") == "bt2020":
            beginning += "-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc"

    if side_data.cll:
        pass

    extra_data = "-map_chapters 0 "  # -map_metadata 0 # safe to do for rotation?
    pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"

    if bitrate:
        command_1 = (
            f"{beginning} -pass 1 "
            f'-passlogfile "{pass_log_file}" -b:v {bitrate} -preset {preset} -an -sn -dn -f mp4 {null}'
        )
        command_2 = (
            f'{beginning} -pass 2 -passlogfile "{pass_log_file}" ' f"-b:v {bitrate} -preset {preset} {extra_data}"
        ) + ending
        return [
            Command(
                re.sub("[ ]+", " ", command_1), ["ffmpeg", "output"], False, name="First pass bitrate", exe="ffmpeg"
            ),
            Command(
                re.sub("[ ]+", " ", command_2), ["ffmpeg", "output"], False, name="Second pass bitrate", exe="ffmpeg"
            ),
        ]

    elif crf:
        command = (f"{beginning} -crf {crf} " f"-preset {preset} {extra_data}") + ending
        return [
            Command(re.sub("[ ]+", " ", command), ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")
        ]

    else:
        return []
