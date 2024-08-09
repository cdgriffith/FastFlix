# -*- coding: utf-8 -*-
import secrets

from fastflix.encoders.common.helpers import Command, generate_filters
from fastflix.models.encode import GIFSettings
from fastflix.models.fastflix import FastFlix
from fastflix.shared import clean_file_string
from fastflix.flix import get_all_concat_items


def build(fastflix: FastFlix):
    settings: GIFSettings = fastflix.current_video.video_settings.video_encoder_settings

    args = f"=stats_mode={settings.stats_mode}"
    if settings.max_colors != "256":
        args += f":max_colors={settings.max_colors}"

    palletgen_filters = generate_filters(
        custom_filters=f"palettegen{args}", **fastflix.current_video.video_settings.model_dump()
    )

    filters = generate_filters(
        custom_filters=f"fps={settings.fps}", raw_filters=True, **fastflix.current_video.video_settings.model_dump()
    )

    output_video = clean_file_string(fastflix.current_video.video_settings.output_path)

    beginning = (
        f'"{fastflix.config.ffmpeg}" -y '
        f'{f"-ss {fastflix.current_video.video_settings.start_time}" if fastflix.current_video.video_settings.start_time else ""} '
        f'{f"-to {fastflix.current_video.video_settings.end_time}" if fastflix.current_video.video_settings.end_time else ""} '
        f'{f"-r {fastflix.current_video.video_settings.source_fps } " if fastflix.current_video.video_settings.source_fps else ""}'
        f' -i "{fastflix.current_video.source}" '
    )
    if settings.extra:
        beginning += f"  "

    temp_palette = fastflix.current_video.work_path / f"temp_palette_{secrets.token_hex(10)}.png"

    command_1 = (
        f'{beginning} {palletgen_filters} {settings.extra if settings.extra_both_passes else ""} -y "{temp_palette}"'
    )

    gif_filters = f"fps={settings.fps}"
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
