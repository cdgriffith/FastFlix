# -*- coding: utf-8 -*-
import logging
import shlex

from fastflix.encoders.common.helpers import Command
from fastflix.models.encode import VCEEncCAVCSettings
from fastflix.models.video import Video
from fastflix.models.fastflix import FastFlix
from fastflix.encoders.common.encc_helpers import (
    build_subtitle,
    build_audio,
    rigaya_auto_options,
    rigaya_avformat_reader,
    pa_builder,
)

logger = logging.getLogger("fastflix")


def build(fastflix: FastFlix):
    video: Video = fastflix.current_video
    settings: VCEEncCAVCSettings = fastflix.current_video.video_settings.video_encoder_settings

    try:
        stream_id = int(video.current_video_stream["id"], 16)
    except Exception:
        if len(video.streams.video) > 1:
            logger.warning("Could not get stream ID from source, the proper video track may not be selected!")
        stream_id = None

    vsync_setting = "cfr" if video.frame_rate == video.average_frame_rate else "vfr"
    if video.video_settings.vsync == "cfr":
        vsync_setting = "forcecfr"
    elif video.video_settings.vsync == "vfr":
        vsync_setting = "vfr"

    output_depth = settings.output_depth
    if not settings.output_depth:
        output_depth = (
            "10"
            if fastflix.current_video.current_video_stream.bit_depth > 8
            and not fastflix.current_video.video_settings.remove_hdr
            else "8"
        )

    command = [
        str(fastflix.config.vceencc),
    ]
    command.extend(rigaya_avformat_reader(fastflix))
    command.extend(["--device", str(settings.device)])
    command.extend(["-i", str(video.source)])

    if stream_id:
        command.extend(["--video-streamid", str(stream_id)])
    if video.video_settings.start_time:
        command.extend(["--seek", str(video.video_settings.start_time)])
    if video.video_settings.end_time:
        command.extend(["--seekto", str(video.video_settings.end_time)])
    if video.video_settings.source_fps:
        command.extend(["--fps", str(video.video_settings.source_fps)])
    if video.video_settings.rotate:
        command.extend(["--vpp-rotate", str(video.video_settings.rotate * 90)])
    if video.video_settings.vertical_flip or video.video_settings.horizontal_flip:
        flip_x = "true" if video.video_settings.horizontal_flip else "false"
        flip_y = "true" if video.video_settings.vertical_flip else "false"
        command.extend(["--vpp-transform", f"flip_x={flip_x},flip_y={flip_y}"])
    if video.scale:
        command.extend(["--output-res", video.scale.replace(":", "x")])
    if video.video_settings.crop:
        crop = video.video_settings.crop
        command.extend(["--crop", f"{crop.left},{crop.top},{crop.right},{crop.bottom}"])

    if video.video_settings.remove_metadata:
        command.extend(["--video-metadata", "clear", "--metadata", "clear"])
    else:
        command.extend(["--video-metadata", "copy", "--metadata", "copy"])

    if video.video_settings.video_title:
        command.extend(["--video-metadata", f"title={video.video_settings.video_title}"])
    if video.video_settings.copy_chapters:
        command.append("--chapter-copy")

    command.extend(["-c", "avc"])

    if settings.bitrate:
        command.extend(["--vbr", settings.bitrate.rstrip("k")])
    else:
        command.extend(["--cqp", str(settings.cqp)])

    if video.video_settings.maxrate:
        command.extend(["--max-bitrate", str(video.video_settings.maxrate)])
        command.extend(["--vbv-bufsize", str(video.video_settings.bufsize)])
    if settings.min_q and settings.bitrate:
        command.extend(["--qp-min", str(settings.min_q)])
    if settings.max_q and settings.bitrate:
        command.extend(["--qp-max", str(settings.max_q)])
    if settings.b_frames:
        command.extend(["--bframes", str(settings.b_frames)])
    if settings.ref:
        command.extend(["--ref", str(settings.ref)])

    command.extend(["--preset", settings.preset])

    if settings.profile.lower() != "auto":
        command.extend(["--profile", settings.profile])

    command.extend(["--level", settings.level or "auto"])
    command.extend(["--output-depth", output_depth])

    command.extend(rigaya_auto_options(fastflix))

    command.extend(["--motion-est", settings.mv_precision])

    if settings.vbaq:
        command.append("--vbaq")
    if settings.pre_encode:
        command.append("--pe")

    pa = pa_builder(settings)
    if pa:
        command.append(pa)

    command.extend(["--avsync", vsync_setting])

    if video.interlaced and video.interlaced != "False":
        command.extend(["--interlace", video.interlaced])
    if video.video_settings.deinterlace:
        command.append("--vpp-nnedi")
    if video.video_settings.remove_hdr:
        remove_type = (
            video.video_settings.tone_map
            if video.video_settings.tone_map in ("mobius", "hable", "reinhard")
            else "mobius"
        )
        command.extend(["--vpp-colorspace", f"hdr2sdr={remove_type}"])
    if settings.split_mode == "parallel":
        command.extend(["--parallel", "auto"])
    if settings.metrics:
        command.extend(["--psnr", "--ssim"])

    command.extend(build_audio(video.audio_tracks, video.streams.audio))
    command.extend(build_subtitle(video.subtitle_tracks, video.streams.subtitle, video_height=video.height))

    if settings.extra:
        command.extend(shlex.split(settings.extra))

    command.extend(["-o", str(video.video_settings.output_path)])

    return [Command(command=command, name="VCEEncC Encode", exe="VCEEncC")]
