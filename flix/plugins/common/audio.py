#!/usr/bin/env python


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        command_list.append(f'-map {audio_file_index}:{track.index}')
        if track.conversion.codec == 'none':
            command_list.append(f'-c:a:{track.index} copy')
        elif 'conversion' in track:
            command_list.append(f'-c:a:{track.index} {track.conversion.codec} '
                                f'-b:a:{track.index} {track.conversion.bitrate} ')

    return " ".join(command_list)

