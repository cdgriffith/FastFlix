# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path
from dataclasses import asdict

from box import Box

from fastflix.encoders.common.audio import build_audio
from fastflix.encoders.common.helpers import Command, generate_ending, generate_ffmpeg_start, generate_filters, null
from fastflix.encoders.common.subtitles import build_subtitle

# from fastflix.models.encode import
from fastflix.models.fastflix import FastFlix
from fastflix.models.encode import x265Settings


def build(
    fastflix: FastFlix,
):
    settings: x265Settings = fastflix.current_video.video_settings.video_encoder_settings

    audio = build_audio(fastflix.current_video.video_settings.audio_tracks)
    subtitles, burn_in_track = build_subtitle(fastflix.current_video.video_settings.subtitle_tracks)
    filters = generate_filters(
        disable_hdr=settings.remove_hdr, burn_in_track=burn_in_track, **asdict(fastflix.current_video.video_settings)
    )
    ending = generate_ending(
        audio=audio,
        subtitles=subtitles,
        # cover=attachments,
        output_video=fastflix.current_video.video_settings.output_path,
    )

    beginning = generate_ffmpeg_start(
        source=fastflix.current_video.source,
        ffmpeg=fastflix.config.ffmpeg,
        encoder="libx265",
        video_track=fastflix.current_video.video_settings.selected_track,
        filters=filters,
        pix_fmt=fastflix.current_video.video_settings.pix_fmt,
    )

    beginning += f'{f"-tune {settings.tune}" if settings.tune else ""} '

    if settings.profile and settings.profile != "default":
        beginning += f"-profile {settings.profile} "

    x265_params = settings.x265_params or []

    x265_params.append(f"aq-mode={settings.aq_mode}")
    x265_params.append(f"repeat-headers={'1' if settings.repeat_headers else '0'}")

    if not settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
        x265_params.append(f"hdr10_opt={'1' if settings.hdr10_opt else '0'}")

        if fastflix.current_video.color_space == "bt2020":
            x265_params.extend(
                [
                    "colorprim=bt2020",
                    "transfer=smpte2084",
                    "colormatrix=bt2020nc",
                ]
            )

        if fastflix.current_video.master_display:
            hdr10 = True
            x265_params.append(
                "master-display="
                f"G{fastflix.current_video.master_display.green}"
                f"B{fastflix.current_video.master_display.blue}"
                f"R{fastflix.current_video.master_display.red}"
                f"WP{fastflix.current_video.master_display.white}"
                f"L{fastflix.current_video.master_display.luminance}"
            )

        if fastflix.current_video.cll:
            hdr10 = True
            x265_params.append(f"max-cll={fastflix.current_video.cll}")

        x265_params.append(f"hdr10={'1' if settings.hdr10 else '0'}")

    if settings.hdr10plus_metadata:
        x265_params.append(f"dhdr10-info='{settings.hdr10plus_metadata}'")

    if settings.intra_encoding:
        x265_params.append("keyint=1")

    if fastflix.current_video.cll:
        pass

    pass_log_file = Path(fastflix.current_video.work_path.name) / f"pass_log_file_{secrets.token_hex(10)}.log"

    def get_x265_params(params=()):
        if not isinstance(params, (list, tuple)):
            params = [params]
        all_params = x265_params + list(params)
        return '-x265-params "{}" '.format(":".join(all_params)) if all_params else ""

    if settings.bitrate:
        command_1 = (
            f'{beginning} {get_x265_params(["pass=1", "no-slow-firstpass=1"])} '
            f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset {settings.preset} -an -sn -dn -f mp4 {null}'
        )
        command_2 = (
            f'{beginning} {get_x265_params(["pass=2"])} -passlogfile "{pass_log_file}" '
            f"-b:v {settings.bitrate} -preset {settings.preset} "
        ) + ending
        return [
            Command(
                re.sub("[ ]+", " ", command_1), ["ffmpeg", "output"], False, name="First pass bitrate", exe="ffmpeg"
            ),
            Command(
                re.sub("[ ]+", " ", command_2), ["ffmpeg", "output"], False, name="Second pass bitrate", exe="ffmpeg"
            ),
        ]

    elif settings.crf:
        command = (f"{beginning} {get_x265_params()}  -crf {settings.crf} " f"-preset {settings.preset} ") + ending
        return [
            Command(re.sub("[ ]+", " ", command), ["ffmpeg", "output"], False, name="Single pass CRF", exe="ffmpeg")
        ]

    else:
        return []
