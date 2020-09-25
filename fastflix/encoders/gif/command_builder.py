# -*- coding: utf-8 -*-
import secrets
from pathlib import Path

from fastflix.encoders.common.helpers import Command, generate_filters

extension = "gif"


def build(
    source,
    video_track,
    ffmpeg,
    temp_dir,
    output_video,
    fps=15,
    dither="sierra2_4a",
    extra="",
    start_time=0,
    end_time=None,
    **kwargs,
):
    filters = generate_filters(**kwargs)

    beginning = (
        f'"{ffmpeg}" -y '
        f'{f"-ss {start_time}" if start_time else ""} '
        f'{f"-to {end_time}" if end_time else ""} '
        f'-i "{source}" '
    )
    if extra:
        beginning += f" {extra} "

    temp_palette = Path(temp_dir) / f"temp_palette_{secrets.token_hex(10)}.png"

    command_1 = (
        f"{beginning} -map 0:{video_track} " f'-vf "{f"{filters}," if filters else ""}palettegen" -y "{temp_palette}"'
    )

    gif_filters = f"fps={fps:.2f}"
    if filters:
        gif_filters += f",{filters}"

    command_2 = (
        f'{beginning} -i "{temp_palette}" -map 0:{video_track} '
        f'-lavfi "{gif_filters} [x]; [x][1:v] paletteuse=dither={dither}" -y "{output_video}" '
    )

    return [
        Command(command_1, ["ffmpeg", "pallet_file", "output"], False, name="Pallet generation", exe="ffmpeg"),
        Command(command_2, ["ffmpeg", "pallet_file", "output"], False, name="GIF creation", exe="ffmpeg"),
    ]
