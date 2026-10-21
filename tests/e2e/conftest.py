# -*- coding: utf-8 -*-
"""
Shared infrastructure for E2E encode tests.

These tests build real FastFlix instances, run real FFmpeg/Rigaya encodes,
and verify output with ffprobe. They are local-only and skip on CI.

Environment variables:
    CI=true         Skip all E2E tests
    SKIP_NVIDIA=1   Skip NVEncC + FFmpeg NVENC encoders
    SKIP_INTEL=1    Skip QSVEncC encoders
    SKIP_AMD=1      Skip VCEEncC encoders
"""

import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pytest
from box import Box
from platformdirs import user_data_dir

from fastflix.flix import guess_bit_depth
from fastflix.models.config import Config
from fastflix.models.encode import (
    AOMAV1Settings,
    AttachmentTrack,
    AudioTrack,
    CopySettings,
    DataTrack,
    FFmpegAV1NVENCSettings,
    SubtitleTrack,
    FFmpegNVENCSettings,
    GIFSettings,
    GifskiSettings,
    NVEncCAV1Settings,
    NVEncCAVCSettings,
    NVEncCSettings,
    QSVEncCAV1Settings,
    QSVEncCH264Settings,
    QSVEncCSettings,
    SVTAV1Settings,
    SVTAVIFSettings,
    VCEEncCAV1Settings,
    H264VideoToolboxSettings,
    HEVCVideoToolboxSettings,
    VCEEncCAVCSettings,
    VCEEncCSettings,
    VP9Settings,
    VVCSettings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
)
from fastflix.models.fastflix import FastFlix
from fastflix.models.video import Video, VideoSettings
from fastflix.widgets.panels.data_panel import NO_ATTACHMENT_EXTENSIONS, NO_DATA_EXTENSIONS

# ---------------------------------------------------------------------------
# CI / hardware skip flags
# ---------------------------------------------------------------------------
ON_CI = os.environ.get("CI", "").lower() in ("true", "1", "yes")
SKIP_NVIDIA = os.environ.get("SKIP_NVIDIA", "").lower() in ("1", "true", "yes")
SKIP_INTEL = os.environ.get("SKIP_INTEL", "").lower() in ("1", "true", "yes")
SKIP_AMD = os.environ.get("SKIP_AMD", "").lower() in ("1", "true", "yes")
SKIP_MAC = os.environ.get("SKIP_MAC", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def _find_rigaya(app_name: str, binary_base: str) -> Optional[str]:
    for name in (f"{binary_base}64", binary_base):
        found = shutil.which(name)
        if found:
            return found
    asset_folder = Path(user_data_dir(app_name, appauthor=False, roaming=True))
    if asset_folder.exists():
        for exe in asset_folder.glob(f"{binary_base}*64.exe"):
            if exe.is_file():
                return str(exe)
        for exe in asset_folder.glob(f"{binary_base}*.exe"):
            if exe.is_file():
                return str(exe)
    return None


NVENCC = _find_rigaya("NVEnc", "NVEncC")
QSVENCC = _find_rigaya("QSVEnc", "QSVEncC")
VCEENCC = _find_rigaya("VCEEnc", "VCEEncC")
GIFSKI = shutil.which("gifski")


def _get_ffmpeg_encoders() -> set[str]:
    if not FFMPEG:
        return set()
    try:
        result = subprocess.run(
            [FFMPEG, "-encoders", "-hide_banner"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        encoders = set()
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and len(parts[0]) == 6:
                encoders.add(parts[1])
        return encoders
    except Exception:
        return set()


_ffmpeg_encoders = _get_ffmpeg_encoders()


def has_ffmpeg_encoder(name: str) -> bool:
    return name in _ffmpeg_encoders


# ---------------------------------------------------------------------------
# Source files
# ---------------------------------------------------------------------------
MEDIA_DIR = Path(__file__).parent.parent / "media"

SOURCES = {
    "hdr10plus": MEDIA_DIR / "Beverly Hills Duck Pond - HDR10plus - Jessica Payne.mp4",
    "attachments": MEDIA_DIR / "font_attachment_data.mkv",
    "chapters": MEDIA_DIR / "chapters_timecode.mp4",
}


# ---------------------------------------------------------------------------
# Probe helper (cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=8)
def probe_source(source_path: str) -> Optional[dict]:
    if not FFPROBE or not Path(source_path).exists():
        return None
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", source_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FastFlix builder
# ---------------------------------------------------------------------------
def create_fastflix(
    source_path: Path,
    encoder_settings,
    output_path: Path,
    work_path: Path,
    is_rigaya: bool = False,
    include_audio: bool = True,
    include_subtitles: bool = False,
    include_data: bool = True,
    include_attachments: bool = True,
) -> FastFlix:
    """Build a real FastFlix instance with tracks from the probed source."""
    probe = probe_source(str(source_path))
    assert probe is not None, f"Could not probe {source_path}"

    ext_with_dot = output_path.suffix.lower()

    # Parse streams by type
    video_streams = [
        s
        for s in probe["streams"]
        if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0
    ]
    audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    subtitle_streams = [s for s in probe["streams"] if s["codec_type"] == "subtitle"]
    data_streams = [s for s in probe["streams"] if s["codec_type"] == "data"]
    attachment_streams = [s for s in probe["streams"] if s.get("codec_type") == "attachment"]

    # Cover images are video streams with attached_pic disposition
    cover_streams = [
        s
        for s in probe["streams"]
        if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic", 0) == 1
    ]

    for stream in video_streams:
        if "bits_per_raw_sample" in stream:
            stream["bit_depth"] = int(stream["bits_per_raw_sample"])
        else:
            stream["bit_depth"] = guess_bit_depth(stream.get("pix_fmt", ""), stream.get("color_primaries"))

    streams = Box(
        {
            "video": [Box(v) for v in video_streams],
            "audio": [Box(a) for a in audio_streams],
            "subtitle": [Box(s) for s in subtitle_streams],
            "data": [Box(d) for d in data_streams],
            "attachment": [Box(a) for a in attachment_streams],
        }
    )

    video_settings = VideoSettings(
        remove_hdr=False,
        output_path=output_path,
        end_time=2,
    )
    video_settings.video_encoder_settings = encoder_settings

    video = Video(
        source=source_path,
        duration=float(probe.get("format", {}).get("duration", 10)),
        streams=streams,
        format=Box(probe.get("format", {})),
        video_settings=video_settings,
        work_path=work_path,
    )

    # --- Audio tracks ---
    if include_audio:
        outdex = 1  # after video
        for stream in audio_streams:
            video.audio_tracks.append(
                AudioTrack(
                    index=stream["index"],
                    outdex=outdex,
                    codec=stream.get("codec_name", ""),
                    enabled=True,
                    raw_info=Box(stream),
                )
            )
            outdex += 1

    # --- Subtitle tracks ---
    if include_subtitles:
        sub_outdex = 1 + len(video.audio_tracks)
        for stream in subtitle_streams:
            dispositions = {k: bool(v) for k, v in stream.get("disposition", {}).items()}
            video.subtitle_tracks.append(
                SubtitleTrack(
                    index=stream["index"],
                    outdex=sub_outdex,
                    language=stream.get("tags", {}).get("language", ""),
                    title=stream.get("tags", {}).get("title", ""),
                    subtitle_type=stream.get("codec_name", "text"),
                    enabled=True,
                    dispositions=dispositions,
                    raw_info=Box(stream),
                )
            )
            sub_outdex += 1

    # --- Data / attachment tracks ---
    data_outdex = 1 + len(video.audio_tracks) + len(video.subtitle_tracks)

    if include_data:
        for stream in data_streams:
            codec_name = stream.get("codec_name", "")
            title = stream.get("tags", {}).get("title", "")
            enabled = ext_with_dot not in NO_DATA_EXTENSIONS
            video.data_tracks.append(
                DataTrack(
                    index=stream["index"],
                    outdex=data_outdex if enabled else 0,
                    enabled=enabled,
                    codec_name=codec_name,
                    codec_type="data",
                    title=title,
                )
            )
            if enabled:
                data_outdex += 1

        for stream in attachment_streams:
            mimetype = stream.get("tags", {}).get("mimetype", "")
            filename = stream.get("tags", {}).get("filename", "")
            # Skip cover images (handled separately)
            if mimetype.startswith("image"):
                continue
            enabled = ext_with_dot not in NO_ATTACHMENT_EXTENSIONS
            video.data_tracks.append(
                DataTrack(
                    index=stream["index"],
                    outdex=data_outdex if enabled else 0,
                    enabled=enabled,
                    codec_name=stream.get("codec_name", ""),
                    codec_type="attachment",
                    mimetype=mimetype,
                    filename=filename,
                )
            )
            if enabled:
                data_outdex += 1

    # --- Cover attachment (extract from source if present) ---
    if include_attachments and cover_streams:
        cover_stream = cover_streams[0]
        cover_ext = "png" if "png" in cover_stream.get("codec_name", "") else "jpg"
        cover_path = work_path / f"cover.{cover_ext}"
        subprocess.run(
            [FFMPEG, "-y", "-i", str(source_path), "-map", f"0:{cover_stream['index']}", "-c", "copy", str(cover_path)],
            capture_output=True,
            timeout=30,
        )
        if cover_path.exists():
            video.attachment_tracks.append(
                AttachmentTrack(
                    index=cover_stream["index"],
                    outdex=data_outdex,
                    file_path=str(cover_path),
                    filename="cover",
                    attachment_type="cover",
                )
            )

    # --- Config ---
    config = Config(
        version="4.0.0",
        ffmpeg=Path(FFMPEG),
        ffprobe=Path(FFPROBE),
        work_path=work_path,
    )
    if is_rigaya:
        if NVENCC:
            config.nvencc = Path(NVENCC)
        if QSVENCC:
            config.qsvencc = Path(QSVENCC)
        if VCEENCC:
            config.vceencc = Path(VCEENCC)
    if GIFSKI:
        config.gifski = Path(GIFSKI)

    return FastFlix(
        config=config,
        encoders={},
        audio_encoders=[],
        current_video=video,
        ffmpeg_version="n5.0",
    )


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------
def run_commands(commands, work_path: Path):
    for cmd in commands:
        cmd_to_run = cmd.to_string() if cmd.shell else cmd.to_list()
        result = subprocess.run(
            cmd_to_run,
            capture_output=True,
            text=True,
            timeout=120,
            shell=cmd.shell,
            cwd=str(work_path),
        )
        assert result.returncode == 0, (
            f"Command '{cmd.name}' failed (exit {result.returncode}):\n"
            f"CMD: {cmd.to_string()}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )


# ---------------------------------------------------------------------------
# Output verifier
# ---------------------------------------------------------------------------
def verify_output(output_path: Path, expected_codec: str) -> dict:
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    assert output_path.stat().st_size > 0, f"Output file is empty: {output_path}"

    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(output_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"

    data = json.loads(result.stdout)
    video_streams = [
        s
        for s in data["streams"]
        if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0
    ]
    assert len(video_streams) >= 1, "No video stream in output"
    actual_codec = video_streams[0]["codec_name"]
    assert actual_codec == expected_codec, f"Expected codec {expected_codec}, got {actual_codec}"
    return data


def verify_lossless_quality(source_path: Path, output_path: Path, end_time: float = 2):
    """Verify lossless encode by comparing per-frame MD5 checksums.

    Decodes both the source (trimmed to end_time) and the lossless output to raw
    video frames and computes MD5 per frame. Every frame MD5 must match, proving
    the encoder preserved pixels exactly with zero quality loss.
    """
    source_result = subprocess.run(
        [FFMPEG, "-to", str(end_time), "-i", str(source_path), "-map", "0:v", "-f", "framemd5", "-"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert source_result.returncode == 0, f"framemd5 on source failed: {source_result.stderr[-1000:]}"

    output_result = subprocess.run(
        [FFMPEG, "-i", str(output_path), "-map", "0:v", "-f", "framemd5", "-"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert output_result.returncode == 0, f"framemd5 on output failed: {output_result.stderr[-1000:]}"

    # Parse frame lines (skip comment lines starting with #)
    source_frames = [line for line in source_result.stdout.splitlines() if line and not line.startswith("#")]
    output_frames = [line for line in output_result.stdout.splitlines() if line and not line.startswith("#")]

    assert len(source_frames) > 0, "No frames decoded from source"
    assert len(output_frames) > 0, "No frames decoded from output"
    assert len(source_frames) == len(output_frames), (
        f"Frame count mismatch: source={len(source_frames)}, output={len(output_frames)}"
    )

    # Extract MD5 hashes (last field in each framemd5 line)
    mismatched = []
    for i, (src_line, out_line) in enumerate(zip(source_frames, output_frames)):
        src_md5 = src_line.split(",")[-1].strip()
        out_md5 = out_line.split(",")[-1].strip()
        if src_md5 != out_md5:
            mismatched.append(f"Frame {i}: source={src_md5} output={out_md5}")

    assert not mismatched, (
        f"Lossless verification failed — {len(mismatched)}/{len(source_frames)} frames differ:\n"
        + "\n".join(mismatched[:10])
    )


# ---------------------------------------------------------------------------
# Encoder definitions
# ---------------------------------------------------------------------------
def _skip_if(*conditions):
    """Return True if ANY condition is True (meaning test should skip)."""
    return lambda: any(c() if callable(c) else c for c in conditions)


# (encoder_id, settings, output_ext, expected_codec, skip_condition, is_rigaya)
FFMPEG_ENCODERS = [
    (
        "hevc_x265",
        x265Settings(preset="ultrafast", crf=51),
        ".mkv",
        "hevc",
        lambda: not has_ffmpeg_encoder("libx265"),
        False,
    ),
    (
        "avc_x264",
        x264Settings(preset="ultrafast", crf=51, pix_fmt="yuv420p"),
        ".mkv",
        "h264",
        lambda: not has_ffmpeg_encoder("libx264"),
        False,
    ),
    ("svt_av1", SVTAV1Settings(speed="13", qp=63), ".mkv", "av1", lambda: not has_ffmpeg_encoder("libsvtav1"), False),
    (
        "av1_aom",
        AOMAV1Settings(cpu_used="8", usage="realtime", crf=63),
        ".mkv",
        "av1",
        lambda: not has_ffmpeg_encoder("libaom-av1"),
        False,
    ),
    ("rav1e", rav1eSettings(speed="10", qp=255), ".mkv", "av1", lambda: not has_ffmpeg_encoder("librav1e"), False),
    (
        "vp9",
        VP9Settings(speed="5", quality="realtime", crf=63, single_pass=True),
        ".mkv",
        "vp9",
        lambda: not has_ffmpeg_encoder("libvpx-vp9"),
        False,
    ),
    ("vvc", VVCSettings(preset="faster", qp=51), ".mkv", "vvc", lambda: not has_ffmpeg_encoder("libvvenc"), False),
    ("copy", CopySettings(), ".mkv", "h264", lambda: False, False),
]

NVIDIA_ENCODERS = [
    (
        "ffmpeg_hevc_nvenc",
        FFmpegNVENCSettings(preset="p1", bitrate="1000k"),
        ".mkv",
        "hevc",
        _skip_if(lambda: not has_ffmpeg_encoder("hevc_nvenc"), lambda: SKIP_NVIDIA),
        False,
    ),
    (
        "ffmpeg_av1_nvenc",
        FFmpegAV1NVENCSettings(preset="p1", bitrate="1000k"),
        ".mkv",
        "av1",
        _skip_if(lambda: not has_ffmpeg_encoder("av1_nvenc"), lambda: SKIP_NVIDIA),
        False,
    ),
    (
        "nvencc_hevc",
        NVEncCSettings(preset="performance", bitrate="1000k"),
        ".mkv",
        "hevc",
        _skip_if(lambda: not NVENCC, lambda: SKIP_NVIDIA),
        True,
    ),
    (
        "nvencc_avc",
        NVEncCAVCSettings(preset="performance", bitrate="1000k"),
        ".mkv",
        "h264",
        _skip_if(lambda: not NVENCC, lambda: SKIP_NVIDIA),
        True,
    ),
    (
        "nvencc_av1",
        NVEncCAV1Settings(preset="performance", bitrate="1000k"),
        ".mkv",
        "av1",
        _skip_if(lambda: not NVENCC, lambda: SKIP_NVIDIA),
        True,
    ),
]

INTEL_ENCODERS = [
    (
        "qsvencc_hevc",
        QSVEncCSettings(preset="fastest", bitrate="1000k"),
        ".mkv",
        "hevc",
        _skip_if(lambda: not QSVENCC, lambda: SKIP_INTEL),
        True,
    ),
    (
        "qsvencc_avc",
        QSVEncCH264Settings(preset="fastest", bitrate="1000k"),
        ".mkv",
        "h264",
        _skip_if(lambda: not QSVENCC, lambda: SKIP_INTEL),
        True,
    ),
    (
        "qsvencc_av1",
        QSVEncCAV1Settings(preset="fastest", bitrate="1000k"),
        ".mkv",
        "av1",
        _skip_if(lambda: not QSVENCC, lambda: SKIP_INTEL),
        True,
    ),
]

AMD_ENCODERS = [
    (
        "vceencc_hevc",
        VCEEncCSettings(preset="fast", bitrate="1000k"),
        ".mkv",
        "hevc",
        _skip_if(lambda: not VCEENCC, lambda: SKIP_AMD),
        True,
    ),
    (
        "vceencc_avc",
        VCEEncCAVCSettings(preset="fast", bitrate="1000k"),
        ".mkv",
        "h264",
        _skip_if(lambda: not VCEENCC, lambda: SKIP_AMD),
        True,
    ),
    (
        "vceencc_av1",
        VCEEncCAV1Settings(preset="fast", bitrate="1000k"),
        ".mkv",
        "av1",
        _skip_if(lambda: not VCEENCC, lambda: SKIP_AMD),
        True,
    ),
]

GIF_ENCODERS = [
    ("gif", GIFSettings(fps="5"), ".gif", "gif", lambda: False, False),
    ("gifski", GifskiSettings(fps="5", fast=True, quality="1"), ".gif", "gif", lambda: not GIFSKI, False),
    (
        "webp",
        WebPSettings(compression="0", qscale=1),
        ".webp",
        "webp",
        lambda: not has_ffmpeg_encoder("libwebp"),
        False,
    ),
    (
        "svt_av1_avif",
        SVTAVIFSettings(speed="13", qp=63),
        ".avif",
        "av1",
        lambda: not has_ffmpeg_encoder("libsvtav1"),
        False,
    ),
]

LOSSLESS_ENCODERS = [
    (
        "hevc_x265",
        x265Settings(preset="ultrafast", lossless=True),
        ".mkv",
        "hevc",
        lambda: not has_ffmpeg_encoder("libx265"),
        False,
    ),
    (
        "avc_x264",
        x264Settings(preset="ultrafast", lossless=True, pix_fmt="yuv420p10le"),
        ".mkv",
        "h264",
        lambda: not has_ffmpeg_encoder("libx264"),
        False,
    ),
    (
        "av1_aom",
        AOMAV1Settings(cpu_used="8", usage="realtime", lossless=True),
        ".mkv",
        "av1",
        lambda: not has_ffmpeg_encoder("libaom-av1"),
        False,
    ),
    (
        "vp9",
        VP9Settings(speed="5", quality="realtime", lossless=True, single_pass=True),
        ".mkv",
        "vp9",
        lambda: not has_ffmpeg_encoder("libvpx-vp9"),
        False,
    ),
    (
        "svt_av1",
        SVTAV1Settings(speed="13", lossless=True),
        ".mkv",
        "av1",
        lambda: not has_ffmpeg_encoder("libsvtav1"),
        False,
    ),
    (
        "webp",
        WebPSettings(lossless="yes", compression="0"),
        ".webp",
        "webp",
        lambda: not has_ffmpeg_encoder("libwebp"),
        False,
    ),
]

MAC_ENCODERS = [
    (
        "hevc_videotoolbox",
        HEVCVideoToolboxSettings(q=50),
        ".mp4",
        "hevc",
        _skip_if(lambda: not has_ffmpeg_encoder("hevc_videotoolbox"), lambda: SKIP_MAC),
        False,
    ),
    (
        "h264_videotoolbox",
        H264VideoToolboxSettings(q=50),
        ".mp4",
        "h264",
        _skip_if(lambda: not has_ffmpeg_encoder("h264_videotoolbox"), lambda: SKIP_MAC),
        False,
    ),
]

ALL_ENCODERS = FFMPEG_ENCODERS + NVIDIA_ENCODERS + INTEL_ENCODERS + AMD_ENCODERS + MAC_ENCODERS + GIF_ENCODERS

# Encoders that support audio/subtitles/data/attachments (not GIF/image formats)
FULL_FEATURE_ENCODERS = FFMPEG_ENCODERS + NVIDIA_ENCODERS + INTEL_ENCODERS + AMD_ENCODERS + MAC_ENCODERS


def make_params(encoder_list):
    """Convert encoder tuples into pytest.param entries with proper skip marks."""
    return [
        pytest.param(
            enc_id,
            settings,
            ext,
            codec,
            is_rigaya,
            id=enc_id,
            marks=pytest.mark.skipif(skip_fn(), reason=f"{enc_id}: required tool not available"),
        )
        for enc_id, settings, ext, codec, skip_fn, is_rigaya in encoder_list
    ]
