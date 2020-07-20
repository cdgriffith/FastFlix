# -*- coding: utf-8 -*-
import reusables
import re

from fastflix.plugins.common import helpers
from fastflix.plugins.common.audio import build_audio


def build(source, video_track, bitrate=None, crf=None, start_time=0, duration=None, audio_tracks=(), **kwargs):
    filters = helpers.generate_filters(**kwargs)
    audio = build_audio(audio_tracks)

    ending = "dev/null && \\"
    if reusables.win_based:
        ending = "NUL"

    beginning = (
        f'"{{ffmpeg}}" -y '
        f' {f"-ss {start_time}" if start_time else ""}  '
        f'{f"-t {duration}" if duration else ""} '
        f'-i "{source}" '
        f"-map 0:{video_track} "
        f"-c:v libaom-av1 -strict experimental "
        f'{f"-vf {filters}" if filters else ""} '
    )

    beginning = re.sub("[ ]+", " ", beginning)

    if bitrate:
        command_1 = f'{beginning} -passlogfile "<tempfile.1.log>" -b:v {bitrate} -pass 1 -an -f matroska {ending}'
        command_2 = f'{beginning} -passlogfile "<tempfile.1.log>" -b:v {bitrate} -pass 2 {audio} "{{output}}"'
        return [
            helpers.Command(command_1, ["ffmpeg", "output"], False, name="First Pass bitrate"),
            helpers.Command(command_2, ["ffmpeg", "output"], False, name="Second Pass bitrate"),
        ]
    elif crf:
        command_1 = f'{beginning} -b:v 0 -crf {crf} {audio} "{{output}}"'
        return [helpers.Command(command_1, ["ffmpeg", "output"], False, name="Single Pass CRF")]
