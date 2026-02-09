#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import List, Tuple, Union

from fastflix.models.video import SubtitleTrack


def build_subtitle(
    subtitle_tracks: list[SubtitleTrack], subtitle_file_index=0, output_path=None
) -> Tuple[List[str], Union[int, None], Union[str, None]]:
    command_list = []
    burn_in_track = None
    burn_in_type = None
    subs_enabled = False

    # Determine if output is MP4 format (requires mov_text codec for subtitles)
    is_mp4 = False
    if output_path:
        try:
            ext = Path(output_path).suffix.lower()
            is_mp4 = ext in (".mp4", ".m4v")
        except Exception:
            pass

    for track in subtitle_tracks:
        if not track.enabled:
            continue
        if track.burn_in:
            burn_in_track = track.index
            burn_in_type = track.subtitle_type
        else:
            outdex = track.outdex - (1 if burn_in_track else 0)
            # MP4 containers require mov_text codec for text subtitles instead of copy (#481)
            codec = "mov_text" if is_mp4 else "copy"
            file_idx = track.file_index if track.file_index else subtitle_file_index
            command_list.extend(["-map", f"{file_idx}:{track.index}", f"-c:{outdex}", codec])
            added = ""
            for disposition, is_set in track.dispositions.items():
                if is_set:
                    added += f"{disposition}+"
                    if disposition in ("default", "forced"):
                        subs_enabled = True
            if added:
                command_list.extend([f"-disposition:{outdex}", added.rstrip("+")])
            else:
                command_list.extend([f"-disposition:{outdex}", "0"])
            command_list.extend([f"-metadata:s:{outdex}", f"language={track.language}"])
    if not subs_enabled:
        command_list.extend(["-default_mode", "infer_no_subs"])
    return command_list, burn_in_track, burn_in_type
