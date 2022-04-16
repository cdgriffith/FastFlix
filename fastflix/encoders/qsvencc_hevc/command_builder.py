# -*- coding: utf-8 -*-
import logging

from fastflix.encoders.common.helpers import Command
from fastflix.models.encode import QSVEncCSettings
from fastflix.models.video import Video
from fastflix.models.fastflix import FastFlix
from fastflix.encoders.common.encc_helpers import build_subtitle, build_audio
from fastflix.flix import clean_file_string

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    video: Video = fastflix.current_video
    settings: QSVEncCSettings = fastflix.current_video.video_settings.video_encoder_settings

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

    bit_depth = "8"
    if video.current_video_stream.bit_depth > 8 and not video.video_settings.remove_hdr:
        bit_depth = "10"
    if settings.force_ten_bit:
        bit_depth = "10"

    vsync_setting = "cfr" if video.frame_rate == video.average_frame_rate else "vfr"
    if video.video_settings.vsync == "cfr":
        vsync_setting = "forcecfr"
    elif video.video_settings.vsync == "vfr":
        vsync_setting = "vfr"

    command = [
        f'"{clean_file_string(fastflix.config.qsvencc)}"',
        "-i",
        f'"{clean_file_string(video.source)}"',
        (f"--video-streamid {stream_id}" if stream_id else ""),
        trim,
        (f"--vpp-rotate {video.video_settings.rotate * 90}" if video.video_settings.rotate else ""),
        transform,
        (f'--output-res {video.video_settings.scale.replace(":", "x")}' if video.video_settings.scale else ""),
        crop,
        (f"--video-metadata clear" if video.video_settings.remove_metadata else "--video-metadata copy"),
        (f'--video-metadata title="{video.video_settings.video_title}"' if video.video_settings.video_title else ""),
        ("--chapter-copy" if video.video_settings.copy_chapters else ""),
        "-c",
        "hevc",
        (f"--vbr {settings.bitrate.rstrip('k')}" if settings.bitrate else f"--cqp {settings.cqp}"),
        vbv,
        (f"--qp-min {min_q}" if min_q and settings.bitrate else ""),
        (f"--qp-max {max_q}" if max_q and settings.bitrate else ""),
        (f"--bframes {settings.b_frames}" if settings.b_frames else ""),
        (f"--ref {settings.ref}" if settings.ref else ""),
        "--quality",
        settings.preset,
        (f"--la-depth {settings.lookahead}" if settings.lookahead else ""),
        "--level",
        (settings.level or "auto"),
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
        bit_depth,
        "--chromaloc",
        "auto",
        "--colorrange",
        "auto",
        f"--avsync {vsync_setting}",
        (f"--interlace {video.interlaced}" if video.interlaced and video.interlaced != "False" else ""),
        ("--vpp-yadif" if video.video_settings.deinterlace else ""),
        (f"--vpp-colorspace hdr2sdr=mobius" if video.video_settings.remove_hdr else ""),
        remove_hdr,
        "--psnr --ssim" if settings.metrics else "",
        build_audio(video.video_settings.audio_tracks, video.streams.audio),
        build_subtitle(video.video_settings.subtitle_tracks, video.streams.subtitle),
        settings.extra,
        "-o",
        f'"{clean_file_string(video.video_settings.output_path)}"',
    ]

    return [Command(command=" ".join(x for x in command if x), name="QSVEncC Encode", exe="QSVEncC")]
