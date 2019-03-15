from flix.builders.helpers import generate_filters


def build(source, video_track, fps=15, dither="sierra2_4a",
          start_time=0, duration=None, **kwargs):

    #if remove_hdr in ("Yes", "Auto Remove"):

    filters = generate_filters(**kwargs)

    command_1 = (f'{f"-ss {start_time}" if start_time else ""} '
                 f'{f"-t {duration}" if duration else ""} '
                 f'-i "{source}" -map 0:{video_track} '
                 f'-vf "{f"{filters}," if filters else "" }palettegen" -y "{{TEMP_1}}"')

    gif_filters = f"fps={fps:.2f}"
    if filters:
        gif_filters += f",{filters}"

    command_2 = (f'{f"-ss {start_time}" if start_time else ""} '
                 f'{f"-t {duration}" if duration else ""} '
                 f'-i "{source}" -i "{{TEMP_1}}" -map 0:{video_track} '
                 f'-lavfi "{gif_filters} [x]; [x][1:v] paletteuse=dither={dither}" -y "{{output}}" ')

    return command_1, command_2
