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
    x265_params=None,
    intra_encoding=False,
    pix_fmt="yuv420p10le",
    tune=None,
    profile="default",
    attachments="",
    hdr10=False,
    hdr10_opt=False,
    repeat_headers=False,
    hdr10plus_metadata="",
    aq_mode=2,
    **kwargs,
):

    audio = build_audio(audio_tracks)
    subtitles, burn_in_track = build_subtitle(subtitle_tracks)
    filters = generate_filters(video_track=video_track, disable_hdr=disable_hdr, burn_in_track=burn_in_track, **kwargs)
    ending = generate_ending(audio=audio, subtitles=subtitles, cover=attachments, output_video=output_video, **kwargs)

    if not side_data:
        side_data = Box(default_box=True)

    beginning = generate_ffmpeg_start(
        source=source,
        ffmpeg=ffmpeg,
        encoder="libx265",
        video_track=video_track,
        filters=filters,
        pix_fmt=pix_fmt,
        **kwargs,
    )

    beginning += f'{f"-tune {tune}" if tune else ""} '

    if profile and profile != "default":
        beginning += f"-profile {profile} "

    if not x265_params:
        x265_params = []

    x265_params.append(f"aq-mode={aq_mode}")
    x265_params.append(f"repeat-headers={'1' if repeat_headers else '0'}")

    if not disable_hdr and pix_fmt in ("yuv420p10le", "yuv420p12le"):
        x265_params.append(f"hdr10_opt={'1' if hdr10_opt else '0'}")

        if side_data and side_data.get("color_primaries") == "bt2020":
            # hdr/hdr10 and hdr-opt/hdr10-opt are the same thing for different x265 versions
            x265_params.extend(
                [
                    "colorprim=bt2020",
                    "transfer=smpte2084",
                    "colormatrix=bt2020nc",
                ]
            )

        if side_data.master_display:
            hdr10 = True
            x265_params.append(
                "master-display="
                f"G{side_data.master_display.green}"
                f"B{side_data.master_display.blue}"
                f"R{side_data.master_display.red}"
                f"WP{side_data.master_display.white}"
                f"L{side_data.master_display.luminance}"
            )

        if side_data.cll:
            hdr10 = True
            x265_params.append(f"max-cll={side_data.cll}")

        x265_params.append(f"hdr10={'1' if hdr10 else '0'}")

    if hdr10plus_metadata:
        x265_params.append(f"dhdr10-info='{hdr10plus_metadata}'")

    if intra_encoding:
        x265_params.append("keyint=1")

    if side_data.cll:
        pass

    pass_log_file = Path(temp_dir) / f"pass_log_file_{secrets.token_hex(10)}.log"

    def get_x265_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = x265_params + list(params)
        return '-x265-params "{}" '.format(":".join(all_params)) if all_params else ""

    if bitrate:
        command_1 = (
            f'{beginning} {get_x265_params(["pass=1", "no-slow-firstpass=1"])} '
            f'-passlogfile "{pass_log_file}" -b:v {bitrate} -preset {preset} -an -sn -dn -f mp4 {null}'
        )
        command_2 = (
            f'{beginning} {get_x265_params(["pass=2"])} -passlogfile "{pass_log_file}" '
            f"-b:v {bitrate} -preset {preset} "
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
        command = (f"{beginning} {get_x265_params()}  -crf {crf} " f"-preset {preset} ") + ending
        return [
            Command(re.sub("[ ]+", " ", command), ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")
        ]

    else:
        return []
