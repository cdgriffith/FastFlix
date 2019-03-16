from flix.builders.helpers import generate_filters, Command


def build(source, video_track, fps=15, dither="sierra2_4a",
          start_time=0, duration=None, **kwargs):

    filters = generate_filters(**kwargs)

    command_1 = (f'{{ffmpeg}} {f"-ss {start_time}" if start_time else ""} '
                 f'{f"-t {duration}" if duration else ""} '
                 f'-i "{source}" -map 0:{video_track} '
                 f'-vf "{f"{filters}," if filters else "" }palettegen" -y "<tempfile.1.png>"')

    gif_filters = f"fps={fps:.2f}"
    if filters:
        gif_filters += f",{filters}"

    command_2 = (f'{{ffmpeg}} {f"-ss {start_time}" if start_time else ""} '
                 f'{f"-t {duration}" if duration else ""} '
                 f'-i "{source}" -i "<tempfile.1.png>" -map 0:{video_track} '
                 f'-lavfi "{gif_filters} [x]; [x][1:v] paletteuse=dither={dither}" -y "{{output}}" ')

    return [Command(command_1, ['ffmpeg', 'pallet_file', 'output'], False),
            Command(command_2, ['ffmpeg', 'pallet_file', 'output'], False)]
