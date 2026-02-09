# -*- coding: utf-8 -*-
import secrets
import shlex

from fastflix.encoders.common.helpers import Command, generate_filters
from fastflix.models.encode import GIFSettings
from fastflix.models.fastflix import FastFlix
from fastflix.shared import sanitize


def build(fastflix: FastFlix):
    settings: GIFSettings = fastflix.current_video.video_settings.video_encoder_settings
    video_settings = fastflix.current_video.video_settings

    # Get scale from Video property (computed based on resolution_method)
    scale = fastflix.current_video.scale

    # Convert crop to dict if it exists (generate_filters expects dict, not Pydantic model)
    crop = video_settings.crop.model_dump() if video_settings.crop else None

    args = f"=stats_mode={settings.stats_mode}"
    if settings.max_colors != "256":
        args += f":max_colors={settings.max_colors}"

    # Build base filters for fps and scale (applied before palette operations)
    # Scale must use lanczos for better GIF quality
    base_filters = generate_filters(
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
        custom_filters=f"fps={settings.fps}",
        raw_filters=True,
    )

    # Palette generation filters include the base filters + palettegen
    # This returns List[str] since raw_filters=False (default)
    palettegen_filters = generate_filters(
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
        custom_filters=f"fps={settings.fps},palettegen{args}",
    )

    output_video = str(sanitize(fastflix.current_video.video_settings.output_path))

    beginning = [str(fastflix.config.ffmpeg), "-y"]
    if video_settings.start_time:
        beginning.extend(["-ss", str(video_settings.start_time)])
    if video_settings.end_time:
        beginning.extend(["-to", str(video_settings.end_time)])
    if video_settings.source_fps:
        beginning.extend(["-r", str(video_settings.source_fps)])
    beginning.extend(["-i", str(fastflix.current_video.source)])

    temp_palette = fastflix.current_video.work_path / f"temp_palette_{secrets.token_hex(10)}.png"

    extra_both = shlex.split(settings.extra) if settings.extra and settings.extra_both_passes else []
    extra = shlex.split(settings.extra) if settings.extra else []

    command_1 = beginning + palettegen_filters + extra_both + ["-y", str(temp_palette)]

    # For GIF creation, apply same base filters then use palette
    # Format: [base_filters];[v][1:v]paletteuse=dither={dither}[o]
    filter_complex = f"{base_filters};[v][1:v]paletteuse=dither={settings.dither}:diff_mode=rectangle[o]"
    command_2 = (
        beginning
        + ["-i", str(temp_palette)]
        + ["-filter_complex", filter_complex, "-map", "[o]"]
        + extra
        + ["-y", output_video]
    )

    return [
        Command(command=command_1, name="Palette generation", exe="ffmpeg"),
        Command(command=command_2, name="GIF creation", exe="ffmpeg"),
    ]
