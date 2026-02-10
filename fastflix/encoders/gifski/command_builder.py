# -*- coding: utf-8 -*-
import shlex
import subprocess
import sys

from fastflix.encoders.common.helpers import Command, generate_filters
from fastflix.models.encode import GifskiSettings
from fastflix.models.fastflix import FastFlix
from fastflix.shared import sanitize


def build(fastflix: FastFlix):
    settings: GifskiSettings = fastflix.current_video.video_settings.video_encoder_settings
    video_settings = fastflix.current_video.video_settings

    scale = fastflix.current_video.scale
    crop = video_settings.crop.model_dump() if video_settings.crop else None

    filters = generate_filters(
        selected_track=video_settings.selected_track,
        source=fastflix.current_video.source,
        crop=crop,
        scale=scale,
        scale_filter="lanczos",
        rotate=video_settings.rotate,
        vertical_flip=video_settings.vertical_flip,
        horizontal_flip=video_settings.horizontal_flip,
        video_speed=video_settings.video_speed,
        deblock=video_settings.deblock,
        deblock_size=video_settings.deblock_size,
        brightness=video_settings.brightness,
        saturation=video_settings.saturation,
        contrast=video_settings.contrast,
        remove_hdr=video_settings.remove_hdr,
        tone_map=video_settings.tone_map,
        custom_filters=f"fps={settings.fps},format=yuv420p",
        raw_filters=True,
    )

    output_video = str(sanitize(fastflix.current_video.video_settings.output_path))

    # Build FFmpeg command to output yuv4mpegpipe to stdout
    ffmpeg_cmd = [str(fastflix.config.ffmpeg), "-y"]
    if video_settings.start_time:
        ffmpeg_cmd.extend(["-ss", str(video_settings.start_time)])
    if video_settings.end_time:
        ffmpeg_cmd.extend(["-to", str(video_settings.end_time)])
    if video_settings.source_fps:
        ffmpeg_cmd.extend(["-r", str(video_settings.source_fps)])
    ffmpeg_cmd.extend(["-i", str(fastflix.current_video.source)])

    if filters:
        ffmpeg_cmd.extend(["-filter_complex", filters, "-map", "[v]"])
    else:
        ffmpeg_cmd.extend(["-map", f"0:{video_settings.selected_track}"])

    ffmpeg_cmd.extend(["-f", "yuv4mpegpipe", "-"])

    # Build gifski command to read from stdin
    gifski_cmd = [str(fastflix.config.gifski)]
    gifski_cmd.extend(["--fps", str(settings.fps)])
    gifski_cmd.extend(["--quality", str(settings.quality)])

    if settings.lossy_quality != "auto":
        gifski_cmd.extend(["--lossy-quality", str(settings.lossy_quality)])
    if settings.motion_quality != "auto":
        gifski_cmd.extend(["--motion-quality", str(settings.motion_quality)])
    if settings.fast:
        gifski_cmd.append("--fast")

    gifski_cmd.extend(["--width", str(fastflix.current_video.width)])
    gifski_cmd.extend(["--height", str(fastflix.current_video.height)])

    extra = shlex.split(settings.extra) if settings.extra else []
    gifski_cmd.extend(extra)

    gifski_cmd.extend(["-o", output_video, "-"])

    # Build shell pipe command string with proper platform quoting
    if sys.platform == "win32":
        full_command = subprocess.list2cmdline(ffmpeg_cmd) + " | " + subprocess.list2cmdline(gifski_cmd)
    else:
        full_command = shlex.join(ffmpeg_cmd) + " | " + shlex.join(gifski_cmd)

    return [
        Command(
            command=full_command,
            name="GIF (gifski)",
            exe="gifski",
            shell=True,
        ),
    ]
