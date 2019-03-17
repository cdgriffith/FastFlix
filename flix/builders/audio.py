#!/usr/bin/env python
from flix.builders.helpers import generate_filters, Command


def build(audio_tracks, allowed_codec=()):
    command_list = []
    for track in audio_tracks:
        command_list.append(f'-map 0:{track.index}')
        if allowed_codec:
            if 'conversion' in track:
                if track.conversion.codec not in allowed_codec:
                    raise Exception('Invalid codec')
                command_list.append(f'-c:a:{track.index} {track.conversion.codec} -b:a:{track.index} {track.conversion.bitrate} ')
                continue
            if track.codec not in allowed_codec:
                raise Exception('Invalid codec')
            command_list.append(f'-c:a:{track.index} copy')
        else:
            command_list.append(f'-c:a:{track.index} copy')
    return " ".join(command_list)

