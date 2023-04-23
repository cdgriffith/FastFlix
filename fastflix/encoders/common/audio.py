#!/usr/bin/env python
# -*- coding: utf-8 -*-

channel_list = {
    "mono": 1,
    "stereo": 2,
    "2.1": 3,
    "3.0": 3,
    "3.0(back)": 3,
    "3.1": 4,
    "4.0": 4,
    "quad": 4,
    "quad(side)": 4,
    "5.0": 5,
    "5.1": 6,
    "6.0": 6,
    "6.0(front)": 6,
    "hexagonal": 6,
    "6.1": 7,
    "6.1(front)": 7,
    "7.0": 7,
    "7.0(front)": 7,
    "7.1": 8,
    "7.1(wide)": 8,
}

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
            downmix = (
                f"-ac:{track.outdex} {channel_list[track.downmix]} -filter:{track.outdex} aformat=channel_layouts={track.downmix}"
                if track.downmix
                else ""
            )
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"-b:{track.outdex} {track.conversion_bitrate} "
            command_list.append(f"-c:{track.outdex} {track.conversion_codec} {bitrate} {downmix}")

        if getattr(track, "dispositions", None):
            added = ""
            for disposition, is_set in track.dispositions.items():
                if is_set:
                    added += f"{disposition}+"
            if added:
                command_list.append(f"-disposition:{track.outdex} {added.rstrip('+')}")
            else:
                command_list.append(f"-disposition:{track.outdex} 0")

    return " ".join(command_list)
