# -*- coding: utf-8 -*-
from typing import List
import logging

from fastflix.encoders.common.helpers import Command
from fastflix.models.encode import NVEncCAVCSettings
from fastflix.models.video import SubtitleTrack, Video
from fastflix.models.fastflix import FastFlix
from fastflix.flix import unixy

lossless = ["flac", "truehd", "alac", "tta", "wavpack", "mlp"]

logger = logging.getLogger("fastflix")


def build_audio(audio_tracks):
    command_list = []
    copies = []
    track_ids = set()

    for track in audio_tracks:
        if track.index in track_ids:
            logger.warning("NVEncC does not support copy and duplicate of audio tracks!")
        track_ids.add(track.index)
        if track.language:
            command_list.append(f"--audio-metadata {track.outdex}?language={track.language}")
        if not track.conversion_codec or track.conversion_codec == "none":
            copies.append(str(track.outdex))
        elif track.conversion_codec:
            downmix = f"--audio-stream {track.outdex}?:{track.downmix}" if track.downmix else ""
            bitrate = ""
            if track.conversion_codec not in lossless:
                bitrate = f"--audio-bitrate {track.outdex}?{track.conversion_bitrate.rstrip('k')} "
            command_list.append(
                f"{downmix} --audio-codec {track.outdex}?{track.conversion_codec} {bitrate} "
                f"--audio-metadata {track.outdex}?clear"
            )

        if track.title:
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
    settings: NVEncCAVCSettings = fastflix.current_video.video_settings.video_encoder_settings

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
        if "/" in video.frame_rate:
            over, under = [int(x) for x in video.frame_rate.split("/")]
            rate = over / under
        else:
            rate = float(video.frame_rate)
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

    if (video.frame_rate != video.average_frame_rate) and trim:
        logger.warning("Cannot use 'trim' when working with variable frame rate videos")
        trim = ""

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

    vbv = ""
    if video.video_settings.maxrate:
        vbv = f"--max-bitrate {video.video_settings.maxrate} --vbv-bufsize {video.video_settings.bufsize}"

    init_q = settings.init_q_i
    if settings.init_q_i and settings.init_q_p and settings.init_q_b:
        init_q = f"{settings.init_q_i}:{settings.init_q_p}:{settings.init_q_b}"

    min_q = settings.min_q_i
    if settings.min_q_i and settings.min_q_p and settings.min_q_b:
        min_q = f"{settings.min_q_i}:{settings.min_q_p}:{settings.min_q_b}"

    max_q = settings.max_q_i
    if settings.max_q_i and settings.max_q_p and settings.max_q_b:
        max_q = f"{settings.max_q_i}:{settings.max_q_p}:{settings.max_q_b}"

    try:
        stream_id = int(video.current_video_stream["id"], 16)
    except Exception:
        if len(video.streams.video) > 1:
            logger.warning("Could not get stream ID from source, the proper video track may not be selected!")
        stream_id = None

    aq = "--no-aq"
    if settings.aq.lower() == "spatial":
        aq = f"--aq --aq-strength {settings.aq_strength}"
    elif settings.aq.lower() == "temporal":
        aq = f"--aq-temporal --aq-strength {settings.aq_strength}"

    command = [
        f'"{unixy(fastflix.config.nvencc)}"',
        "-i",
        f'"{unixy(video.source)}"',
        (f"--video-streamid {stream_id}" if stream_id else ""),
        trim,
        (f"--vpp-rotate {video.video_settings.rotate}" if video.video_settings.rotate else ""),
        transform,
        (f'--output-res {video.video_settings.scale.replace(":", "x")}' if video.video_settings.scale else ""),
        crop,
        (f"--video-metadata clear" if video.video_settings.remove_metadata else "--video-metadata copy"),
        (f'--video-metadata title="{video.video_settings.video_title}"' if video.video_settings.video_title else ""),
        ("--chapter-copy" if video.video_settings.copy_chapters else ""),
        "-c",
        "avc",
        (f"--vbr {settings.bitrate.rstrip('k')}" if settings.bitrate else f"--cqp {settings.cqp}"),
        vbv,
        (f"--vbr-quality {settings.vbr_target}" if settings.vbr_target is not None and settings.bitrate else ""),
        (f"--qp-init {init_q}" if init_q and settings.bitrate else ""),
        (f"--qp-min {min_q}" if min_q and settings.bitrate else ""),
        (f"--qp-max {max_q}" if max_q and settings.bitrate else ""),
        (f"--bframes {settings.b_frames}" if settings.b_frames else ""),
        (f"--ref {settings.ref}" if settings.ref else ""),
        f"--bref-mode {settings.b_ref_mode}",
        "--preset",
        settings.preset,
        (f"--lookahead {settings.lookahead}" if settings.lookahead else ""),
        aq,
        "--colormatrix",
        (video.video_settings.color_space or "auto"),
        "--transfer",
        (video.video_settings.color_transfer or "auto"),
        "--colorprim",
        (video.video_settings.color_primaries or "auto"),
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
        (f"--vpp-colorspace hdr2sdr=mobius" if video.video_settings.remove_hdr else ""),
        remove_hdr,
        "--psnr --ssim" if settings.metrics else "",
        build_audio(video.video_settings.audio_tracks),
        build_subtitle(video.video_settings.subtitle_tracks),
        settings.extra,
        "-o",
        f'"{unixy(video.video_settings.output_path)}"',
    ]

    return [Command(command=" ".join(x for x in command if x), name="NVEncC Encode", exe="NVEncE")]
