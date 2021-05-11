#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, Tuple, Union

from fastflix.models.video import SubtitleTrack


def build_subtitle(
    subtitle_tracks: List[SubtitleTrack], subtitle_file_index=0
) -> Tuple[str, Union[int, None], Union[str, None]]:
    command_list = []
    burn_in_track = None
    burn_in_type = None
    subs_enabled = False
    for track in subtitle_tracks:
        if track.burn_in:
            burn_in_track = track.index
            burn_in_type = track.subtitle_type
        else:
            outdex = track.outdex - (1 if burn_in_track else 0)
            command_list.append(f"-map {subtitle_file_index}:{track.index} -c:{outdex} copy ")
            if track.disposition:
                command_list.append(f"-disposition:{outdex} {track.disposition}")
                if track.disposition in ("default", "forced"):
                    subs_enabled = True
            else:
                command_list.append(f"-disposition:{outdex} 0")
            command_list.append(f"-metadata:s:{outdex} language='{track.language}'")
    if not subs_enabled:
        command_list.append("-default_mode infer_no_subs")
    return " ".join(command_list), burn_in_track, burn_in_type
