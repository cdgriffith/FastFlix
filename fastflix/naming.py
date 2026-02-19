# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pathvalidate import sanitize_filename

logger = logging.getLogger("fastflix")

MAX_FILENAME_PATH_LENGTH = 250


class VariablePhase(Enum):
    PRE_ENCODE = "pre_encode"
    POST_ENCODE = "post_encode"


@dataclass
class TemplateVariable:
    name: str
    description: str
    phase: VariablePhase
    example: str
    placeholder: str = ""  # For post-encode vars, filesystem-safe placeholder


PRE_ENCODE_VARIABLES = [
    TemplateVariable("source", "Source filename stem", VariablePhase.PRE_ENCODE, "MyMovie"),
    TemplateVariable("datetime", "ISO date+time (queue time)", VariablePhase.PRE_ENCODE, "2026-02-13T14-30-00"),
    TemplateVariable("date", "Date only (queue time)", VariablePhase.PRE_ENCODE, "2026-02-13"),
    TemplateVariable("time", "Time only (queue time)", VariablePhase.PRE_ENCODE, "14-30-00"),
    TemplateVariable("rand_4", "4-char random hex", VariablePhase.PRE_ENCODE, "a3f1"),
    TemplateVariable("rand_8", "8-char random hex", VariablePhase.PRE_ENCODE, "a3f1b2c4"),
    TemplateVariable("encoder", "Short encoder name", VariablePhase.PRE_ENCODE, "x265"),
    TemplateVariable("codec", "Full codec name", VariablePhase.PRE_ENCODE, "HEVC (x265)"),
    TemplateVariable("preset", "Encoder preset", VariablePhase.PRE_ENCODE, "medium"),
    TemplateVariable("crf", "CRF/QP value", VariablePhase.PRE_ENCODE, "22"),
    TemplateVariable("bitrate", "Target bitrate", VariablePhase.PRE_ENCODE, "5000k"),
    TemplateVariable("pix_fmt", "Pixel format", VariablePhase.PRE_ENCODE, "yuv420p10le"),
    TemplateVariable("resolution", "Output resolution", VariablePhase.PRE_ENCODE, "1920x1080"),
    TemplateVariable("source_resolution", "Source resolution", VariablePhase.PRE_ENCODE, "3840x2160"),
    TemplateVariable("source_duration", "Source duration", VariablePhase.PRE_ENCODE, "01-23-45"),
    TemplateVariable("source_fps", "Source frame rate", VariablePhase.PRE_ENCODE, "23.976"),
    TemplateVariable("source_codec", "Source video codec", VariablePhase.PRE_ENCODE, "hevc"),
    TemplateVariable("source_bitrate", "Source overall bitrate", VariablePhase.PRE_ENCODE, "45000k"),
    TemplateVariable("audio_codec", "First audio track codec", VariablePhase.PRE_ENCODE, "aac"),
    TemplateVariable("audio_channels", "First audio channels", VariablePhase.PRE_ENCODE, "5.1"),
    TemplateVariable("color_space", "Color space", VariablePhase.PRE_ENCODE, "bt2020nc"),
    TemplateVariable("color_primaries", "Color primaries", VariablePhase.PRE_ENCODE, "bt2020"),
    TemplateVariable("hdr", "HDR type or SDR", VariablePhase.PRE_ENCODE, "HDR10"),
]

POST_ENCODE_VARIABLES = [
    TemplateVariable("encode_time", "Encode duration", VariablePhase.POST_ENCODE, "00-15-32", "FFETIME"),
    TemplateVariable("encode_end", "Finish timestamp", VariablePhase.POST_ENCODE, "2026-02-13T14-45-32", "FFEEND"),
    TemplateVariable("filesize", "Human-readable size", VariablePhase.POST_ENCODE, "1.5GB", "FFFSIZE"),
    TemplateVariable("filesize_mb", "Size in MB", VariablePhase.POST_ENCODE, "1536", "FFFSMB"),
    TemplateVariable("video_bitrate", "Actual video bitrate", VariablePhase.POST_ENCODE, "4523k", "FFVIDBIT"),
    TemplateVariable("audio_bitrate", "Actual audio bitrate", VariablePhase.POST_ENCODE, "320k", "FFAUDBIT"),
    TemplateVariable("overall_bitrate", "Overall bitrate", VariablePhase.POST_ENCODE, "4843k", "FFALLBIT"),
]

ALL_VARIABLES = PRE_ENCODE_VARIABLES + POST_ENCODE_VARIABLES

_VARIABLE_MAP = {v.name: v for v in ALL_VARIABLES}
_POST_ENCODE_PLACEHOLDERS = {v.placeholder: v for v in POST_ENCODE_VARIABLES}


def safe_format(template: str, variables: dict) -> str:
    """Replace {var} patterns in template with values from variables dict.
    Unknown variables are left as-is."""

    def replacer(match):
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return re.sub(r"\{(\w+)\}", replacer, template)


def _extract_short_encoder_name(full_name: str) -> str:
    """Extract short encoder name from full codec name like 'HEVC (x265)' -> 'x265'."""
    m = re.search(r"\((.+)\)", full_name)
    if m:
        return m.group(1)
    return full_name.replace(" ", "-")


def _format_duration_hms(seconds: float) -> str:
    """Format seconds as HH-MM-SS (filesystem-safe)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}-{minutes:02d}-{secs:02d}"


def _format_bitrate(bps: float) -> str:
    """Format bits per second as human-readable like '4523k'."""
    kbps = int(bps / 1000)
    if kbps >= 1000:
        return f"{kbps}k"
    return f"{kbps}k"


def _format_filesize(size_bytes: int) -> str:
    """Format file size as human-readable."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    return f"{size_bytes / 1024:.1f}KB"


def _get_channel_layout(channels: int) -> str:
    """Convert channel count to common layout name."""
    layouts = {1: "mono", 2: "stereo", 6: "5.1", 8: "7.1"}
    return layouts.get(channels, str(channels))


def _get_hdr_type(video) -> str:
    """Determine HDR type from video metadata."""
    if hasattr(video, "hdr10_plus") and video.hdr10_plus:
        return "HDR10+"
    if hasattr(video, "hdr10_streams") and video.hdr10_streams:
        return "HDR10"
    color_transfer = ""
    if hasattr(video, "color_transfer"):
        color_transfer = video.color_transfer
    if color_transfer == "smpte2084":
        return "HDR10"
    if color_transfer == "arib-std-b67":
        return "HLG"
    return "SDR"


def _safe_value(value: str) -> str:
    """Sanitize a single variable value for use in filenames."""
    return str(sanitize_filename(str(value), replacement_text="-"))


def _eval_frame_rate(fr_string: str) -> str:
    """Evaluate frame rate fraction like '24000/1001' to '23.976'."""
    if not fr_string:
        return "N-A"
    if "/" in fr_string:
        try:
            num, den = fr_string.split("/")
            val = float(num) / float(den)
            return f"{val:.3f}"
        except (ValueError, ZeroDivisionError):
            return fr_string
    return fr_string


def resolve_pre_encode_variables(
    template: str,
    source_path: Path,
    video=None,
    encoder_settings=None,
    video_settings=None,
) -> str:
    """Resolve all pre-encode variables in a template string.

    Inserts placeholders for any post-encode variables present in the template.
    """
    import secrets

    now = datetime.now()
    iso_datetime = now.strftime("%Y-%m-%dT%H-%M-%S")
    date_only = now.strftime("%Y-%m-%d")
    time_only = now.strftime("%H-%M-%S")

    variables = {
        "source": source_path.stem,
        "datetime": iso_datetime,
        "date": date_only,
        "time": time_only,
        "rand_4": secrets.token_hex(2),
        "rand_8": secrets.token_hex(4),
    }

    # Encoder-specific variables
    if encoder_settings is not None:
        full_name = getattr(encoder_settings, "name", "N-A")
        variables["codec"] = full_name
        variables["encoder"] = _extract_short_encoder_name(full_name)
        variables["preset"] = str(getattr(encoder_settings, "preset", "N-A"))

        crf_val = getattr(encoder_settings, "crf", None)
        if crf_val is None:
            crf_val = getattr(encoder_settings, "qp", None)
        variables["crf"] = str(crf_val) if crf_val is not None else "N-A"

        bitrate_val = getattr(encoder_settings, "bitrate", None)
        variables["bitrate"] = str(bitrate_val) if bitrate_val else "N-A"

        variables["pix_fmt"] = str(getattr(encoder_settings, "pix_fmt", "N-A"))
    else:
        for key in ("encoder", "codec", "preset", "crf", "bitrate", "pix_fmt"):
            variables.setdefault(key, "N-A")

    # Source and video variables
    if video is not None:
        variables["source_resolution"] = f"{video.width}x{video.height}"
        variables["source_duration"] = _format_duration_hms(video.duration) if video.duration else "N-A"
        variables["source_fps"] = _eval_frame_rate(video.frame_rate)
        variables["color_space"] = video.color_space or "N-A"
        variables["color_primaries"] = video.color_primaries or "N-A"
        variables["hdr"] = _get_hdr_type(video)

        # Source codec from streams
        if video.streams and video.streams.video:
            stream = video.current_video_stream
            if stream:
                variables["source_codec"] = stream.get("codec_name", "N-A")
            else:
                variables["source_codec"] = "N-A"
        else:
            variables["source_codec"] = "N-A"

        # Source bitrate from format
        if video.format and video.format.get("bit_rate"):
            try:
                bps = int(video.format.bit_rate)
                variables["source_bitrate"] = _format_bitrate(bps)
            except (ValueError, TypeError):
                variables["source_bitrate"] = "N-A"
        else:
            variables["source_bitrate"] = "N-A"

        # Audio info from first audio track
        if video.streams and video.streams.get("audio"):
            audio = video.streams.audio[0]
            variables["audio_codec"] = audio.get("codec_name", "N-A")
            channels = audio.get("channels", 0)
            variables["audio_channels"] = _get_channel_layout(channels)
        else:
            variables["audio_codec"] = "N-A"
            variables["audio_channels"] = "N-A"
    else:
        for key in (
            "source_resolution",
            "source_duration",
            "source_fps",
            "source_codec",
            "source_bitrate",
            "audio_codec",
            "audio_channels",
            "color_space",
            "color_primaries",
            "hdr",
        ):
            variables.setdefault(key, "N-A")

    # Output resolution
    if video_settings is not None and video is not None:
        scale = video.scale
        if scale:
            variables["resolution"] = scale.replace(":", "x").replace("-8", "auto")
        else:
            variables["resolution"] = f"{video.width}x{video.height}"
    else:
        variables["resolution"] = variables.get("source_resolution", "N-A")

    # Sanitize all values for filesystem safety
    variables = {k: _safe_value(v) for k, v in variables.items()}

    # Insert placeholders for post-encode variables
    for var in POST_ENCODE_VARIABLES:
        variables[var.name] = var.placeholder

    return safe_format(template, variables)


def resolve_post_encode_variables(
    filename: str,
    output_path: Path,
    probe_data,
    encode_start: Optional[datetime] = None,
    encode_end: Optional[datetime] = None,
) -> str:
    """Replace post-encode placeholders in a filename with actual values from probe data."""
    replacements = {}

    # Encode time
    if encode_start and encode_end:
        elapsed = (encode_end - encode_start).total_seconds()
        replacements["FFETIME"] = _safe_value(_format_duration_hms(elapsed))
    else:
        replacements["FFETIME"] = "N-A"

    # Encode end timestamp
    if encode_end:
        replacements["FFEEND"] = _safe_value(encode_end.strftime("%Y-%m-%dT%H-%M-%S"))
    else:
        replacements["FFEEND"] = _safe_value(datetime.now().strftime("%Y-%m-%dT%H-%M-%S"))

    # File size
    try:
        size_bytes = output_path.stat().st_size
        replacements["FFFSIZE"] = _safe_value(_format_filesize(size_bytes))
        replacements["FFFSMB"] = str(int(size_bytes / (1024 * 1024)))
    except OSError:
        replacements["FFFSIZE"] = "N-A"
        replacements["FFFSMB"] = "N-A"

    # Bitrate info from probe data
    if probe_data:
        # Overall bitrate
        overall_br = None
        if hasattr(probe_data, "format") and probe_data.format:
            overall_br = probe_data.format.get("bit_rate")
        if overall_br:
            try:
                replacements["FFALLBIT"] = _format_bitrate(int(overall_br))
            except (ValueError, TypeError):
                replacements["FFALLBIT"] = "N-A"
        else:
            replacements["FFALLBIT"] = "N-A"

        # Per-stream bitrates
        video_br = "N-A"
        audio_br = "N-A"
        if hasattr(probe_data, "streams"):
            for stream in probe_data.streams:
                codec_type = stream.get("codec_type", "")
                br = stream.get("bit_rate")
                if codec_type == "video" and br and video_br == "N-A":
                    try:
                        video_br = _format_bitrate(int(br))
                    except (ValueError, TypeError):
                        pass
                elif codec_type == "audio" and br and audio_br == "N-A":
                    try:
                        audio_br = _format_bitrate(int(br))
                    except (ValueError, TypeError):
                        pass
        replacements["FFVIDBIT"] = video_br
        replacements["FFAUDBIT"] = audio_br
    else:
        for key in ("FFALLBIT", "FFVIDBIT", "FFAUDBIT"):
            replacements[key] = "N-A"

    # Do the replacements
    result = filename
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


def has_post_encode_placeholders(filename: str) -> bool:
    """Check if any post-encode placeholders exist in the filename."""
    return any(var.placeholder in filename for var in POST_ENCODE_VARIABLES)


def generate_preview(template: str) -> str:
    """Generate a preview of the template using example values."""
    variables = {}
    for var in ALL_VARIABLES:
        variables[var.name] = var.example
    return safe_format(template, variables)


def validate_template(template: str) -> tuple[bool, str]:
    """Validate a template string. Returns (is_valid, message)."""
    if not template.strip():
        return False, "Template cannot be empty"

    unknown = []
    for match in re.finditer(r"\{(\w+)\}", template):
        name = match.group(1)
        if name not in _VARIABLE_MAP:
            unknown.append(name)

    if unknown:
        return False, f"Unknown variable(s): {', '.join('{' + n + '}' for n in unknown)}"

    return True, "Valid template"


def truncate_filename(name: str, directory: str, extension: str) -> tuple[str, bool]:
    """Truncate the filename stem so the full path stays within MAX_FILENAME_PATH_LENGTH.

    Returns (possibly_truncated_name, was_truncated).
    The directory and extension lengths are accounted for.
    """
    # +1 for the path separator between directory and filename
    overhead = len(directory) + 1 + len(extension)
    max_name_len = MAX_FILENAME_PATH_LENGTH - overhead

    if max_name_len < 10:
        # Directory path is extremely long, allow at least 10 chars for the name
        max_name_len = 10

    if len(name) <= max_name_len:
        return name, False

    truncated = name[:max_name_len]
    logger.info(
        f"Output filename truncated from {len(name)} to {max_name_len} chars (path limit {MAX_FILENAME_PATH_LENGTH})"
    )
    return truncated, True
