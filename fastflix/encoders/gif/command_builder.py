# -*- coding: utf-8 -*-
import secrets
from pathlib import Path

from fastflix.encoders.common.helpers import Command, generate_filters, start_and_input

extension = "gif"


def build(source, video_track, ffmpeg, temp_dir, fps=15, dither="sierra2_4a", **kwargs):

    filters = generate_filters(**kwargs)

    beginning = start_and_input(source, ffmpeg, **kwargs)

    temp_palette = Path(temp_dir) / f"temp_palette_{secrets.token_hex(10)}.png"

    command_1 = (
        f"{beginning} -map 0:{video_track} " f'-vf "{f"{filters}," if filters else "" }palettegen" -y "{temp_palette}"'
    )

    gif_filters = f"fps={fps:.2f}"
    if filters:
        gif_filters += f",{filters}"

    command_2 = (
        f'{beginning} -i "{temp_palette}" -map 0:{video_track} '
        f'-lavfi "{gif_filters} [x]; [x][1:v] paletteuse=dither={dither}" -y "{{output}}" '
    )

    return [
        Command(command_1, ["ffmpeg", "pallet_file", "output"], False, name="Pallet generation", exe="ffmpeg"),
        Command(command_2, ["ffmpeg", "pallet_file", "output"], False, name="GIF creation", exe="ffmpeg"),
    ]
