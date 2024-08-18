# -*- coding: utf-8 -*-
import logging

from fastflix.encoders.common.helpers import Command
from fastflix.models.encode import NVEncCSettings
from fastflix.models.video import Video
from fastflix.models.fastflix import FastFlix
from fastflix.encoders.common.encc_helpers import (
    build_subtitle,
    build_audio,
    rigaya_auto_options,
    rigaya_avformat_reader,
)
from fastflix.flix import clean_file_string

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    video: Video = fastflix.current_video
    settings: NVEncCSettings = fastflix.current_video.video_settings.video_encoder_settings

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
    if settings.copy_hdr10:
        dhdr = f"--dhdr10-info copy"

    seek = ""
    seekto = ""
    if video.video_settings.start_time:
        seek = f"--seek {video.video_settings.start_time}"
    if video.video_settings.end_time:
        seekto = f"--seekto {video.video_settings.end_time}"

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

    source_fps = f"--fps {video.video_settings.source_fps}" if video.video_settings.source_fps else ""

    command = [
        f'"{clean_file_string(fastflix.config.nvencc)}"',
        rigaya_avformat_reader(fastflix),
        "--device",
        str(settings.device),
        "-i",
        f'"{clean_file_string(video.source)}"',
        (f"--video-streamid {stream_id}" if stream_id else ""),
        seek,
        seekto,
        source_fps,
        (f"--vpp-rotate {video.video_settings.rotate * 90}" if video.video_settings.rotate else ""),
        transform,
        (f'--output-res {video.scale.replace(":", "x")}' if video.scale else ""),
        crop,
        (
            f"--video-metadata clear --metadata clear"
            if video.video_settings.remove_metadata
            else "--video-metadata copy  --metadata copy"
        ),
        (f'--video-metadata title="{video.video_settings.video_title}"' if video.video_settings.video_title else ""),
        ("--chapter-copy" if video.video_settings.copy_chapters else ""),
        "-c",
        "hevc",
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
        "--tier",
        settings.tier,
        (f"--lookahead {settings.lookahead}" if settings.lookahead else ""),
        aq,
        "--level",
        (settings.level or "auto"),
        rigaya_auto_options(fastflix),
        (master_display if master_display else ""),
        (max_cll if max_cll else ""),
        (dhdr if dhdr else ""),
        "--output-depth",
        bit_depth,
        "--multipass",
        settings.multipass,
        "--mv-precision",
        settings.mv_precision,
        f"--avsync {vsync_setting}",
        (f"--interlace {video.interlaced}" if video.interlaced and video.interlaced != "False" else ""),
        ("--vpp-yadif" if video.video_settings.deinterlace else ""),
        remove_hdr,
        "--psnr --ssim" if settings.metrics else "",
        build_audio(video.audio_tracks, video.streams.audio),
        build_subtitle(video.subtitle_tracks, video.streams.subtitle, video_height=video.height),
        settings.extra,
        "-o",
        f'"{clean_file_string(video.video_settings.output_path)}"',
    ]

    return [Command(command=" ".join(x for x in command if x), name="NVEncC Encode", exe="NVEncE")]
