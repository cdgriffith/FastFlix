# -*- coding: utf-8 -*-
import re
import secrets
from pathlib import Path

from fastflix.encoders.common.helpers import Command, generate_all, null
from fastflix.models.encode import x265Settings
from fastflix.models.fastflix import FastFlix


def build(fastflix: FastFlix):
    settings: x265Settings = fastflix.current_video.video_settings.video_encoder_settings

    beginning, ending = generate_all(fastflix, "libx265")

    if settings.tune and settings.tune != "default":
        beginning += f"-tune {settings.tune}"

    if settings.profile and settings.profile != "default":
        beginning += f"-profile {settings.profile} "

    x265_params = settings.x265_params or []

    x265_params.append(f"aq-mode={settings.aq_mode}")
    x265_params.append(f"repeat-headers={'1' if settings.repeat_headers else '0'}")

    if not settings.remove_hdr and settings.pix_fmt in ("yuv420p10le", "yuv420p12le"):
        x265_params.append(f"hdr10_opt={'1' if settings.hdr10_opt else '0'}")

        if fastflix.current_video.color_space.startswith("bt2020"):
            x265_params.extend(["colorprim=bt2020", "transfer=smpte2084", "colormatrix=bt2020nc"])

        if fastflix.current_video.master_display:
            settings.hdr10 = True
            x265_params.append(
                "master-display="
                f"G{fastflix.current_video.master_display.green}"
                f"B{fastflix.current_video.master_display.blue}"
                f"R{fastflix.current_video.master_display.red}"
                f"WP{fastflix.current_video.master_display.white}"
                f"L{fastflix.current_video.master_display.luminance}"
            )

        if fastflix.current_video.cll:
            settings.hdr10 = True
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
            f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset {settings.preset}'
            f" -an -sn -dn -f mp4 {null}"
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
