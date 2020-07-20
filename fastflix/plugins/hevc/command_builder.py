# -*- coding: utf-8 -*-
import reusables
import re

from box import Box

from fastflix.plugins.common.helpers import generate_filters, Command
from fastflix.plugins.common.audio import build_audio
from fastflix.plugins.common.subtitles import build_subtitle


def build(
    source,
    video_track,
    bitrate=None,
    crf=None,
    start_time=0,
    duration=None,
    preset="fast",
    audio_tracks=(),
    subtitle_tracks=(),
    disable_hdr=False,
    side_data=None,
    x265_params=None,
    intra_encoding=False,
    max_mux="default",
    extra="",
    **kwargs,
):
    filters = generate_filters(disable_hdr=disable_hdr, **kwargs)
    audio = build_audio(audio_tracks)
    subtitles = build_subtitle(subtitle_tracks)

    ending = "dev/null && \\"
    if reusables.win_based:
        ending = "NUL"

    if not side_data:
        side_data = Box(default_box=True)

    beginning = (
        f'"{{ffmpeg}}" -y '
        f'-i "{source}" '
        f' {f"-ss {start_time}" if start_time else ""}  '
        f'{f"-to {duration}" if duration else ""} '
        f"{extra} "
        f"-map 0:{video_track} "
        # "-pix_fmt yuv420p10le "
        f"-c:v libx265 "
        f'{f"-vf {filters}" if filters else ""} '
        # f'{"-pix_fmt yuv420p" if force420 else ""} '
    )

    beginning = re.sub("[ ]+", " ", beginning)

    if max_mux and max_mux != "default":
        beginning += f"-max_muxing_queue_size {max_mux} "

    if not x265_params:
        x265_params = []

    if not disable_hdr:
        if side_data.color_primaries == "bt2020":
            x265_params.extend(
                ["hdr-opt=1", "repeat-headers=1", "colorprim=bt2020", "transfer=smpte2084", "colormatrix=bt2020nc"]
            )

        if side_data.master_display:
            x265_params.append(
                "master-display="
                f"G{side_data.master_display.green}"
                f"B{side_data.master_display.blue}"
                f"R{side_data.master_display.red}"
                f"WP{side_data.master_display.white}"
                f"L{side_data.master_display.luminance}"
            )

        if side_data.cll:
            x265_params.append(f"max-cll={side_data.cll}")

    if intra_encoding:
        x265_params.append("keyint=1")

    if x265_params:
        beginning += '-x265-params "{}" '.format(":".join(x265_params))

    if side_data.cll:
        pass

    extra_data = "-map_chapters 0 "  # -map_metadata 0 # safe to do for rotation?

    if bitrate:
        command_1 = f'{beginning}:pass=1 -passlogfile "<tempfile.1.log>" -b:v {bitrate} -an -f mp4 {ending}'
        command_2 = (
            f'{beginning}:pass=2 -passlogfile "<tempfile.1.log>" '
            f'-b:v {bitrate} -preset {preset} {audio} {subtitles} {extra_data} "{{output}}"'
        )
        return [
            Command(command_1, ["ffmpeg", "output"], False, name="First pass bitrate", exe="ffmpeg"),
            Command(command_2, ["ffmpeg", "output"], False, name="Second pass bitrate", exe="ffmpeg"),
        ]

    elif crf:
        command = f'{beginning} -crf {crf} -preset {preset} {audio} {subtitles} {extra_data} "{{output}}"'
        return [Command(command, ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")]

    else:
        return []
