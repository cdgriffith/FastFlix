# -*- coding: utf-8 -*-
from typing import List, Dict
import logging

from fastflix.models.video import SubtitleTrack, AudioTrack
from fastflix.encoders.common.audio import lossless


logger = logging.getLogger("fastflix")


def get_stream_pos(streams) -> Dict:
    return {x.index: i for i, x in enumerate(streams, start=1)}


def build_audio(audio_tracks: List[AudioTrack], audio_streams):
    command_list = []
    copies = []
    track_ids = set()
    stream_ids = get_stream_pos(audio_streams)

    for track in sorted(audio_tracks, key=lambda x: x.outdex):
        if track.index in track_ids:
            logger.warning("*EncC does not support copy and duplicate of audio tracks!")
        track_ids.add(track.index)
        audio_id = stream_ids[track.index]
        if track.language:
            command_list.append(f"--audio-metadata {audio_id}?language={track.language}")
        if not track.conversion_codec or track.conversion_codec == "none":
            copies.append(str(audio_id))
        elif track.conversion_codec:
            downmix = f"--audio-stream {audio_id}?:{track.downmix}" if track.downmix else ""
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"--audio-bitrate {audio_id}?{track.conversion_bitrate.rstrip('k')} "
            command_list.append(
                f"{downmix} --audio-codec {audio_id}?{track.conversion_codec} {bitrate} "
                f"--audio-metadata {audio_id}?clear"
            )

        if track.title:
            command_list.append(
                f'--audio-metadata {audio_id}?title="{track.title}" '
                f'--audio-metadata {audio_id}?handler="{track.title}" '
            )

    return f" --audio-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"


def build_subtitle(subtitle_tracks: List[SubtitleTrack], subtitle_streams, video_height: int) -> str:
    command_list = []
    copies = []
    stream_ids = get_stream_pos(subtitle_streams)

    scale = ",scale=2.0" if video_height > 1800 else ""

    for track in sorted(subtitle_tracks, key=lambda x: x.outdex):
        sub_id = stream_ids[track.index]
        if track.burn_in:
            command_list.append(f"--vpp-subburn track={sub_id}{scale}")
        else:
            copies.append(str(sub_id))
            if track.disposition:
                command_list.append(f"--sub-disposition {sub_id}?{track.disposition}")
            else:
                command_list.append(f"--sub-disposition {sub_id}?unset")
            command_list.append(f"--sub-metadata  {sub_id}?language='{track.language}'")

    commands = f" --sub-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"
    if commands:
        return f"{commands} -m default_mode:infer_no_subs"
    return ""
