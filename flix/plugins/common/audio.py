#!/usr/bin/env python
# -*- coding: utf-8 -*-


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        downmix = f"-ac:{track.index} {track.downmix}" if track.downmix > 0 else ""
        command_list.append(
            f"-map {audio_file_index}:{track.outdex} "
            f'-metadata:s:{track.index} title="{track.title}" '
            f'-metadata:s:{track.index} handler="{track.title}"'
        )
        if track.conversion.codec == "none":
            command_list.append(f"-c:a:{track.index} copy")
        elif "conversion" in track:
            command_list.append(
                f"-c:{track.index} {track.conversion.codec} -b:{track.index} {track.conversion.bitrate} {downmix}"
            )

    return " ".join(command_list)
