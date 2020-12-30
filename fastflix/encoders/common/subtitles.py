#!/usr/bin/env python
# -*- coding: utf-8 -*-


def build_subtitle(subtitle_tracks, subtitle_file_index=0):
    command_list = []
    burn_in_track = None
    for track in subtitle_tracks:
        if track.burn_in:
            burn_in_track = track.index
        else:
            outdex = track.outdex - (1 if burn_in_track else 0)
            command_list.append(f"-map {subtitle_file_index}:{track.index} -c:{outdex} copy ")
            if track.disposition:
                command_list.append(f"-disposition:{outdex} {track.disposition}")
            else:
                command_list.append(f"-disposition:{outdex} 0")
            command_list.append(f"-metadata:s:{outdex} language='{track.language}'")

    return " ".join(command_list), burn_in_track
