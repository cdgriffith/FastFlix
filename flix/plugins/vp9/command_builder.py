import reusables
import re

from flix.builders.helpers import generate_filters, Command
from flix.builders.audio import build as build_audio


def build(source, video_track, bitrate=None, crf=None, start_time=0, duration=None, single_pass=False,
          quality='good', audio_tracks=(), speed=1, **kwargs):
    filters = generate_filters(**kwargs)
    audio = build_audio(audio_tracks)

    ending = "dev/null && \\"
    if reusables.win_based:
        ending = "NUL"

    beginning = (f'"{{ffmpeg}}" -y '
                 f' {f"-ss {start_time}" if start_time else ""}  '
                 f'{f"-t {duration}" if duration else ""} '
                 f'-i "{source}" '
                 f'-map 0:{video_track} '
                 f'-c:v libvpx-vp9 '
                 f'{f"-vf {filters}" if filters else ""} '
                 f'-passlogfile "<tempfile.1.log>" ')

    beginning = re.sub('[ ]+', ' ', beginning)

    if bitrate:
        command_1 = f'{beginning} -b:v {bitrate} -quality good -speed 4 -pass 1 -an -f webm {ending}'
        command_2 = f'{beginning} -b:v {bitrate}  -quality {quality} -speed {speed} -pass 2 {audio} "{{output}}"'

    elif crf:
        command_1 = f'{beginning} -b:v 0 -crf {crf} -quality good -speed 4 -pass 1 -an -f webm {ending}'
        command_2 = f'{beginning} -b:v 0 -crf {crf} -quality {quality} -speed {speed} -pass 2 {audio} "{{output}}"'

    else:
        return []

    if crf and single_pass:
        return [Command(command_2, ['ffmpeg', 'output'], False)]
    return [Command(command_1, ['ffmpeg', 'output'], False),
            Command(command_2, ['ffmpeg', 'output'], False)]
