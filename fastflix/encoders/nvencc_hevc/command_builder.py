# -*- coding: utf-8 -*-
import re
import secrets
from typing import List, Tuple, Union
import logging

from fastflix.encoders.common.helpers import Command, generate_all, generate_color_details, null
from fastflix.models.encode import NVEncCSettings
from fastflix.models.video import SubtitleTrack, Video
from fastflix.models.fastflix import FastFlix
from fastflix.flix import unixy

lossless = ["flac", "truehd", "alac", "tta", "wavpack", "mlp"]

logger = logging.getLogger("fastflix")


def build_audio(audio_tracks):
    command_list = []
    copies = []

    for track in audio_tracks:
        if track.language:
            command_list.append(f"--audio-metadata {track.outdex}?language={track.language}")
        if not track.conversion_codec or track.conversion_codec == "none":
            copies.append(str(track.outdex))
        elif track.conversion_codec:
            downmix = f"--audio-stream {track.outdex}?:{track.downmix}" if track.downmix else ""
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"--audio-bitrate {track.outdex}?{track.conversion_bitrate.rstrip('k')} "
            command_list.append(f"{downmix} --audio-codec {track.outdex}?{track.conversion_codec} {bitrate}")
        command_list.append(
            f'--audio-metadata {track.outdex}?title="{track.title}" '
            f'--audio-metadata {track.outdex}?handler="{track.title}" '
        )

    return f" --audio-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"


def build_subtitle(subtitle_tracks: List[SubtitleTrack]) -> str:
    command_list = []
    copies = []
    for i, track in enumerate(subtitle_tracks, start=1):
        if track.burn_in:
            command_list.append(f"--vpp-subburn track={i}")
        else:
            copies.append(str(i))
            if track.disposition:
                command_list.append(f"--sub-disposition {i}?{track.disposition}")
            command_list.append(f"--sub-metadata  {i}?language='{track.language}'")

    return f" --sub-copy {','.join(copies)} {' '.join(command_list)}" if copies else f" {' '.join(command_list)}"


def build(fastflix: FastFlix):
    video: Video = fastflix.current_video
    settings: NVEncCSettings = fastflix.current_video.video_settings.video_encoder_settings

    # beginning, ending = generate_all(fastflix, "hevc_nvenc")

    # beginning += f'{f"-tune:v {settings.tune}" if settings.tune else ""} {generate_color_details(fastflix)} -spatial_aq:v {settings.spatial_aq} -tier:v {settings.tier} -rc-lookahead:v {settings.rc_lookahead} -gpu {settings.gpu} -b_ref_mode {settings.b_ref_mode} '

    # --profile main10 --tier main

    video_track = 0
    for i, track in enumerate(video.streams.video):
        if int(track.index) == video.video_settings.selected_track:
            video_track = i

    master_display = None
    if fastflix.current_video.master_display:
        master_display = (
            f'--master-display "G{fastflix.current_video.master_display.green}'
            f"B{fastflix.current_video.master_display.blue}"
            f"R{fastflix.current_video.master_display.red}"
            f"WP{fastflix.current_video.master_display.white}"
            f'L{fastflix.current_video.master_display.luminance}"'
        )

    max_cll = None
    if fastflix.current_video.cll:
        max_cll = f'--max-cll "{fastflix.current_video.cll}"'

    dhdr = None
    if settings.hdr10plus_metadata:
        dhdr = f'--dhdr10-info "{settings.hdr10plus_metadata}"'

    trim = ""
    try:
        rate = video.average_frame_rate or video.frame_rate
        if "/" in rate:
            over, under = [int(x) for x in rate.split("/")]
            rate = over / under
        else:
            rate = float(rate)
    except Exception:
        logger.exception("Could not get framerate of this movie!")
    else:
        if video.video_settings.end_time:
            end_frame = int(video.video_settings.end_time * rate)
            start_frame = 0
            if video.video_settings.start_time:
                start_frame = int(video.video_settings.start_time * rate)
            trim = f"--trim {start_frame}:{end_frame}"
        elif video.video_settings.start_time:
            trim = f"--seek {video.video_settings.start_time}"

    transform = ""
    if video.video_settings.vertical_flip or video.video_settings.horizontal_flip:
        transform = f"--vpp-transform flip_x={'true' if video.video_settings.horizontal_flip else 'false'},flip_y={'true' if video.video_settings.vertical_flip else 'false'}"

    remove_hdr = ""
    if video.video_settings.remove_hdr:
        remove_type = (
            video.video_settings.tone_map
            if video.video_settings.tone_map in ("mobius", "hable", "reinhard")
            else "mobius"
        )
        remove_hdr = f"--vpp-colorspace hdr2sdr={remove_type}" if video.video_settings.remove_hdr else ""

    crop = ""
    if video.video_settings.crop:
        crop = f"--crop {video.video_settings.crop.left},{video.video_settings.crop.top},{video.video_settings.crop.right},{video.video_settings.crop.bottom}"

    command = [
        f'"{unixy(fastflix.config.nvencc)}"',
        "-i",
        f'"{unixy(video.source)}"',
        f"--video-streamid {video_track}",
        trim,
        (f"--vpp-rotate {video.video_settings.rotate}" if video.video_settings.rotate else ""),
        transform,
        (f'--output-res {video.video_settings.scale.replace(":", "x")}' if video.video_settings.scale else ""),
        crop,
        (f"--video-metadata 1?clear" if video.video_settings.remove_metadata else "--video-metadata 1?copy"),
        (f'--video-metadata 1?title="{video.video_settings.video_title}"' if video.video_settings.video_title else ""),
        ("--chapter-copy" if video.video_settings.copy_chapters else ""),
        "-c",
        "hevc",
        (f"--vbr {settings.bitrate}" if settings.bitrate else f"--cqp {settings.cqp}"),
        (f"--qp-init {settings.init_q}" if settings.init_q else ""),
        (f"--qp-min {settings.min_q}" if settings.min_q else ""),
        (f"--qp-max {settings.max_q}" if settings.max_q else ""),
        "--preset",
        settings.preset,
        "--profile",
        settings.profile,
        "--tier",
        settings.tier,
        (f"--lookahead {settings.lookahead}" if settings.lookahead else ""),
        ("--aq" if settings.spatial_aq else "--no-aq"),
        "--colormatrix",
        (video.video_settings.color_space or "auto"),
        "--transfer",
        (video.video_settings.color_transfer or "auto"),
        "--colorprim",
        (video.video_settings.color_primaries or "auto"),
        (master_display if master_display else ""),
        (max_cll if max_cll else ""),
        (dhdr if dhdr else ""),
        "--output-depth",
        ("10" if video.current_video_stream.bit_depth > 8 and not video.video_settings.remove_hdr else "8"),
        "--multipass",
        settings.multipass,
        "--mv-precision",
        settings.mv_precision,
        "--chromaloc",
        "auto",
        "--colorrange",
        "auto",
        f"--avsync {'cfr' if video.frame_rate == video.average_frame_rate else 'vfr'}",
        (f"--interlace {video.interlaced}" if video.interlaced else ""),
        ("--vpp-yadif" if video.video_settings.deinterlace else ""),
        (f"--output-res {video.video_settings.scale}" if video.video_settings.scale else ""),
        (f"--vpp-colorspace hdr2sdr=mobius" if video.video_settings.remove_hdr else ""),
        remove_hdr,
        build_audio(video.video_settings.audio_tracks),
        build_subtitle(video.video_settings.subtitle_tracks),
        settings.extra,
        "-o",
        f'"{unixy(video.video_settings.output_path)}"',
    ]

    return [Command(command=" ".join(command), name="NVEncC Encode", exe="NVEncE")]


# -i "Beverly Hills Duck Pond - HDR10plus - Jessica Payne.mp4" -c hevc --profile main10 --tier main --output-depth 10 --vbr 6000k --preset quality --multipass 2pass-full --aq --repeat-headers --colormatrix bt2020nc --transfer smpte2084 --colorprim bt2020 --lookahead 16 -o "nvenc-6000k.mkv"

#
# if settings.profile:
#     beginning += f"-profile:v {settings.profile} "
#
# if settings.rc:
#     beginning += f"-rc:v {settings.rc} "
#
# if settings.level:
#     beginning += f"-level:v {settings.level} "
#
# pass_log_file = fastflix.current_video.work_path / f"pass_log_file_{secrets.token_hex(10)}"
#
# command_1 = (
#     f"{beginning} -pass 1 "
#     f'-passlogfile "{pass_log_file}" -b:v {settings.bitrate} -preset:v {settings.preset} -2pass 1 '
#     f'{settings.extra if settings.extra_both_passes else ""} -an -sn -dn -f mp4 {null}'
# )
# command_2 = (
#     f'{beginning} -pass 2 -passlogfile "{pass_log_file}" -2pass 1 '
#     f"-b:v {settings.bitrate} -preset:v {settings.preset} {settings.extra} "
# ) + ending
# return [
#     Command(command=re.sub("[ ]+", " ", command_1), name="First pass bitrate", exe="ffmpeg"),
#     Command(command=re.sub("[ ]+", " ", command_2), name="Second pass bitrate", exe="ffmpeg"),
# ]
