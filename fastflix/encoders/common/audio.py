#!/usr/bin/env python
# -*- coding: utf-8 -*-

lossless = ["flac", "truehd", "alac", "tta", "wavpack", "mlp"]


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        command_list.append(
            f"-map {audio_file_index}:{track.index} "
            f'-metadata:s:{track.outdex} title="{track.title}" '
            f'-metadata:s:{track.outdex} handler="{track.title}"'
        )
        if track.language:
            command_list.append(f"-metadata:s:{track.outdex} language={track.language}")
        if not track.conversion_codec or track.conversion_codec == "none":
            command_list.append(f"-c:{track.outdex} copy")
        elif track.conversion_codec:
            downmix = f"-ac:{track.outdex} {track.downmix}" if track.downmix > 0 else ""
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"-b:{track.outdex} {track.conversion_bitrate} "
            command_list.append(f"-c:{track.outdex} {track.conversion_codec} {bitrate} {downmix}")

    return " ".join(command_list)
