#!/usr/bin/env python
# -*- coding: utf-8 -*-


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        downmix = f"-ac {track.downmix}" if track.downmix > 0 else ""
        command_list.append(
            f"-map {audio_file_index}:{track.index} "
            f'-metadata:s:{track.outdex} title="{track.title}" '
            f'-metadata:s:{track.outdex} handler="{track.title}"'
        )
        if track.conversion.codec == "none":
            # command_list.append(f"-c:a:{track.outdex-1} copy")
            command_list.append(f"-c:{track.outdex} copy")
        elif "conversion" in track:
            command_list.append(
                f"-c:{track.outdex} {track.conversion.codec} -b:a:{track.outdex} {track.conversion.bitrate} {downmix}"
            )

    return " ".join(command_list)
