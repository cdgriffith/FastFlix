#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from typing import List, Tuple, Union

from fastflix.models.video import SubtitleTrack

logger = logging.getLogger("fastflix")

BITMAP_SUBTITLE_TYPES = ("picture", "pgs")
MP4_EXTENSIONS = (".mp4", ".m4v", ".mov")
MATROSKA_EXTENSIONS = (".mkv", ".mka", ".mks", ".mk3d", ".webm")


def build_subtitle(
    subtitle_tracks: list[SubtitleTrack], subtitle_file_index=0, output_path=None
) -> Tuple[List[str], Union[int, None], Union[str, None]]:
    command_list = []
    burn_in_track = None
    burn_in_type = None
    subs_enabled = False

    # Determine if output is MP4 format (requires mov_text codec for subtitles)
    is_mp4 = False
    # -default_mode is a Matroska muxer option, other muxers reject it
    is_matroska = True
    if output_path:
        try:
            ext = Path(output_path).suffix.lower()
            is_mp4 = ext in MP4_EXTENSIONS
            is_matroska = ext in MATROSKA_EXTENSIONS
        except Exception:
            pass

    removed = 0

    for track in subtitle_tracks:
        if not track.enabled:
            continue
        if track.burn_in:
            burn_in_track = track.index
            burn_in_type = track.subtitle_type
            removed += 1
        elif is_mp4 and track.subtitle_type in BITMAP_SUBTITLE_TYPES:
            # Bitmap subtitles cannot be converted to mov_text, mapping them would fail the encode
            logger.warning(f"Skipping bitmap subtitle track {track.index}, not supported in MP4/MOV containers")
            removed += 1
        else:
            outdex = track.outdex - removed
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
            if track.title:
                command_list.extend([f"-metadata:s:{outdex}", f"title={track.title}"])
                command_list.extend([f"-metadata:s:{outdex}", f"handler={track.title}"])
            else:
                command_list.extend([f"-metadata:s:{outdex}", "title="])
                command_list.extend([f"-metadata:s:{outdex}", "handler="])
    if not subs_enabled and is_matroska:
        command_list.extend(["-default_mode", "infer_no_subs"])
    return command_list, burn_in_track, burn_in_type
