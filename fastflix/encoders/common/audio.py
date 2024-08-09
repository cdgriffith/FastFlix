#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger("fastflix")

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
    "5.1(side)": 6,
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


def audio_quality_converter(quality, codec, channels=2, track_number=1):
    base = [120, 96, 72, 48, 24, 24, 16, 8, 8, 8][quality]

    match codec:
        case "libopus":
            return f" -vbr:{track_number} on -b:{track_number} {base * channels}k "
        case "aac":
            return f" -q:{track_number} {[2, 1.8, 1.6, 1.4, 1.2, 1, 0.8, 0.6, 0.4, 0.2][quality]} "
        case "libfdk_aac":
            return f" -q:{track_number} {[1, 1, 2, 2, 3, 3, 4, 4, 5, 5][quality]} "
        case "libvorbis" | "vorbis":
            return f" -q:{track_number} {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1][quality]} "
        case "libmp3lame" | "mp3":
            return f" -q:{track_number} {quality} "
        case "ac3" | "eac3" | "truehd":
            return f" -b:{track_number} {base * channels * 4}k "
        case _:
            return f" -b:{track_number} {base * channels}k "


def build_audio(audio_tracks, audio_file_index=0):
    command_list = []
    for track in audio_tracks:
        if not track.enabled:
            continue
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
            try:
                cl = track.downmix if track.downmix and track.downmix != "No Downmix" else track.raw_info.channel_layout
            except (AssertionError, KeyError):
                cl = "stereo"
                logger.warning("Could not determine channel layout, defaulting to stereo, please manually specify")

            downmix = (
                f"-ac:{track.outdex} {channel_list[cl]}" if track.downmix and track.downmix != "No Downmix" else ""
            )
            channel_layout = f'-filter:{track.outdex} "aformat=channel_layouts={cl}"'

            bitrate = ""
            if track.conversion_codec not in lossless:
                if track.conversion_bitrate:
                    conversion_bitrate = (
                        track.conversion_bitrate
                        if track.conversion_bitrate.lower().endswith(("k", "m", "g", "kb", "mb", "gb"))
                        else f"{track.conversion_bitrate}k"
                    )

                    bitrate = f"-b:{track.outdex} {conversion_bitrate}"
                else:
                    bitrate = audio_quality_converter(
                        track.conversion_aq, track.conversion_codec, track.raw_info.get("channels"), track.outdex
                    )

            command_list.append(f"-c:{track.outdex} {track.conversion_codec} {bitrate} {downmix} {channel_layout}")

        if getattr(track, "dispositions", None):
            added = ""
            for disposition, is_set in track.dispositions.items():
                if is_set:
                    added += f"{disposition}+"
            if added:
                command_list.append(f"-disposition:{track.outdex} {added.rstrip('+')}")
            else:
                command_list.append(f"-disposition:{track.outdex} 0")

    end_command = " ".join(command_list)
    if " truehd " in end_command or " opus " in end_command or " dca " in end_command:
        end_command += " -strict -2 "
    return end_command
