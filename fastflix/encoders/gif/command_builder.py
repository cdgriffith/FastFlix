# -*- coding: utf-8 -*-
import secrets

from fastflix.encoders.common.helpers import Command, generate_filters
from fastflix.models.encode import GIFSettings
from fastflix.models.fastflix import FastFlix
from fastflix.shared import clean_file_string


def build(fastflix: FastFlix):
    settings: GIFSettings = fastflix.current_video.video_settings.video_encoder_settings

    palletgen_filters = generate_filters(custom_filters="palettegen", **fastflix.current_video.video_settings.dict())

    filters = generate_filters(
        custom_filters=f"fps={settings.fps:.2f}", raw_filters=True, **fastflix.current_video.video_settings.dict()
    )

    output_video = clean_file_string(fastflix.current_video.video_settings.output_path)
    beginning = (
        f'"{fastflix.config.ffmpeg}" -y '
        f'{f"-ss {fastflix.current_video.video_settings.start_time}" if fastflix.current_video.video_settings.start_time else ""} '
        f'{f"-to {fastflix.current_video.video_settings.end_time}" if fastflix.current_video.video_settings.end_time else ""} '
        f'-i "{fastflix.current_video.source}" '
    )
    if settings.extra:
        beginning += f"  "

    temp_palette = fastflix.current_video.work_path / f"temp_palette_{secrets.token_hex(10)}.png"

    command_1 = (
        f'{beginning} {palletgen_filters} {settings.extra if settings.extra_both_passes else ""} -y "{temp_palette}"'
    )

    gif_filters = f"fps={settings.fps:.2f}"
    if filters:
        gif_filters += f",{filters}"

    command_2 = (
        f'{beginning} -i "{temp_palette}" '
        f'-filter_complex "{filters};[v][1:v]paletteuse=dither={settings.dither}[o]" -map "[o]" {settings.extra} -y "{output_video}" '
    )

    return [
        Command(command=command_1, name="Pallet generation", exe="ffmpeg"),
        Command(command=command_2, name="GIF creation", exe="ffmpeg"),
    ]
