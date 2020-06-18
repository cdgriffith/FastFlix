#!/usr/bin/env python
# -*- coding: utf-8 -*-


def build_subtitle(subtitle_tracks, subtitle_file_index=0):
    command_list = []
    for track in subtitle_tracks:
        command_list.append(f"-map {subtitle_file_index}:{track.index} -c:{track.outdex} copy ")
        command_list.append(f"-disposition:s:{track.outdex} {track.disposition}")
        command_list.append(f"-metadata:s:{track.outdex} language={track.language}")

    return " ".join(command_list)
