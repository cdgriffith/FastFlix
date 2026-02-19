# -*- coding: utf-8 -*-
"""
Local-only integration tests that build real encoder commands and execute them.

These tests:
1. Build actual encoder commands (no mocking)
2. Execute them against a real test video
3. Verify output with ffprobe
4. Skip on CI (GitHub Actions sets CI=true)
5. Skip encoders whose tools aren't installed

Run:
    uv run pytest tests/test_local_encode.py -v
    uv run pytest tests/test_local_encode.py -v -k "x265"
    CI=true uv run pytest tests/test_local_encode.py -v  # all skipped
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest
from box import Box
from platformdirs import user_data_dir

from fastflix.models.config import Config
from fastflix.models.encode import (
    AOMAV1Settings,
    CopySettings,
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
    VCEEncCAVCSettings,
    VCEEncCSettings,
    VP9Settings,
    VVCSettings,
    WebPSettings,
    rav1eSettings,
    x264Settings,
    x265Settings,
)
from fastflix.flix import guess_bit_depth
from fastflix.models.fastflix import FastFlix
from fastflix.models.video import Video, VideoSettings

# ---------------------------------------------------------------------------
# Skip everything on CI
# ---------------------------------------------------------------------------
pytestmark = [pytest.mark.local_only]

ON_CI = os.environ.get("CI", "").lower() in ("true", "1", "yes")
if ON_CI:
    pytestmark.append(pytest.mark.skip(reason="Local-only tests skipped on CI"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TEST_SOURCE = Path(__file__).parent / "media" / "Beverly Hills Duck Pond - HDR10plus - Jessica Payne.mp4"
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

if not FFMPEG or not FFPROBE:
    pytestmark.append(pytest.mark.skip(reason="ffmpeg/ffprobe not found"))


# ---------------------------------------------------------------------------
# Detect available FFmpeg encoders
# ---------------------------------------------------------------------------
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


def _has_ffmpeg_encoder(name: str) -> bool:
    return name in _ffmpeg_encoders


# Rigaya tools - check PATH first, then FastFlix's download locations in AppData
def _find_rigaya(app_name: str, binary_base: str) -> Optional[str]:
    """Find a Rigaya encoder binary, checking PATH then FastFlix's AppData download folder."""
    for name in (f"{binary_base}64", binary_base):
        found = shutil.which(name)
        if found:
            return found
    # Check FastFlix's download location
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


# ---------------------------------------------------------------------------
# Probe the source video once at module level
# ---------------------------------------------------------------------------
def _probe_source() -> Optional[dict]:
    if not FFPROBE or not TEST_SOURCE.exists():
        return None
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(TEST_SOURCE)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except Exception:
        return None


_source_probe = _probe_source()


# ---------------------------------------------------------------------------
# Helper: create a real FastFlix instance from probed data
# ---------------------------------------------------------------------------
def create_real_fastflix(encoder_settings, output_path: Path, work_path: Path, is_rigaya: bool = False) -> FastFlix:
    probe = _source_probe
    assert probe is not None, "Could not probe source video"

    video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
    audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    subtitle_streams = [s for s in probe["streams"] if s["codec_type"] == "subtitle"]
    data_streams = [s for s in probe["streams"] if s["codec_type"] == "data"]
    attachment_streams = [s for s in probe["streams"] if s.get("codec_type") == "attachment"]

    # Add bit_depth like FastFlix's flix.py does during probe parsing
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
        maxrate=None,
        bufsize=None,
        output_path=output_path,
        end_time=1,
    )
    video_settings.video_encoder_settings = encoder_settings

    video = Video(
        source=TEST_SOURCE,
        duration=float(probe.get("format", {}).get("duration", 10)),
        streams=streams,
        format=Box(probe.get("format", {})),
        video_settings=video_settings,
        work_path=work_path,
    )

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

    fastflix = FastFlix(
        config=config,
        encoders={},
        audio_encoders=[],
        current_video=video,
        ffmpeg_version="n5.0",
    )

    return fastflix


# ---------------------------------------------------------------------------
# Helper: verify output with ffprobe
# ---------------------------------------------------------------------------
def verify_output(output_path: Path, expected_codec: str):
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    assert output_path.stat().st_size > 0, f"Output file is empty: {output_path}"

    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", str(output_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"

    data = json.loads(result.stdout)
    video_streams = [s for s in data["streams"] if s["codec_type"] == "video"]
    assert len(video_streams) >= 1, "No video stream in output"
    actual_codec = video_streams[0]["codec_name"]
    assert actual_codec == expected_codec, f"Expected codec {expected_codec}, got {actual_codec}"


# ---------------------------------------------------------------------------
# Helper: run a Command list
# ---------------------------------------------------------------------------
def run_commands(commands, work_path: Path):
    for cmd in commands:
        if cmd.shell:
            cmd_to_run = cmd.to_string()
        else:
            cmd_to_run = cmd.to_list()
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


# ===========================================================================
# Encoder test definitions
# ===========================================================================

ENCODER_TESTS = []


def _add(encoder_id, settings, output_ext, expected_codec, skip_condition, is_rigaya=False):
    ENCODER_TESTS.append(
        pytest.param(
            encoder_id,
            settings,
            output_ext,
            expected_codec,
            is_rigaya,
            id=encoder_id,
            marks=pytest.mark.skipif(skip_condition(), reason=f"{encoder_id}: required tool not available"),
        )
    )


# --- FFmpeg-based encoders ---
_add(
    "hevc_x265",
    x265Settings(preset="ultrafast", crf=51),
    ".mkv",
    "hevc",
    lambda: not _has_ffmpeg_encoder("libx265"),
)
_add(
    "avc_x264",
    x264Settings(preset="ultrafast", crf=51, pix_fmt="yuv420p"),
    ".mkv",
    "h264",
    lambda: not _has_ffmpeg_encoder("libx264"),
)
_add(
    "svt_av1",
    SVTAV1Settings(speed="13", qp=63),
    ".mkv",
    "av1",
    lambda: not _has_ffmpeg_encoder("libsvtav1"),
)
_add(
    "av1_aom",
    AOMAV1Settings(cpu_used="8", usage="realtime", crf=63),
    ".mkv",
    "av1",
    lambda: not _has_ffmpeg_encoder("libaom-av1"),
)
_add(
    "rav1e",
    rav1eSettings(speed="10", qp=255),
    ".mkv",
    "av1",
    lambda: not _has_ffmpeg_encoder("librav1e"),
)
_add(
    "vp9",
    VP9Settings(speed="5", quality="realtime", crf=63, single_pass=True),
    ".mkv",
    "vp9",
    lambda: not _has_ffmpeg_encoder("libvpx-vp9"),
)
_add(
    "vvc",
    VVCSettings(preset="faster", qp=51),
    ".mkv",
    "vvc",
    lambda: not _has_ffmpeg_encoder("libvvenc"),
)
_add(
    "webp",
    WebPSettings(compression="0", qscale=1),
    ".webp",
    "webp",
    lambda: not _has_ffmpeg_encoder("libwebp"),
)
_add(
    "gif",
    GIFSettings(fps="5"),
    ".gif",
    "gif",
    lambda: False,  # GIF uses built-in FFmpeg filter, always available
)
_add(
    "gifski",
    GifskiSettings(fps="5", fast=True, quality="1"),
    ".gif",
    "gif",
    lambda: not GIFSKI,
)
_add(
    "svt_av1_avif",
    SVTAVIFSettings(speed="13", qp=63),
    ".avif",
    "av1",
    lambda: not _has_ffmpeg_encoder("libsvtav1"),
)
_add(
    "ffmpeg_hevc_nvenc",
    FFmpegNVENCSettings(preset="p1", bitrate="1000k"),
    ".mkv",
    "hevc",
    lambda: not _has_ffmpeg_encoder("hevc_nvenc"),
)
_add(
    "copy",
    CopySettings(),
    ".mkv",
    "hevc",  # Source is HEVC, copy preserves codec
    lambda: False,
)

# --- NVEncC ---
_add(
    "nvencc_hevc",
    NVEncCSettings(preset="performance", bitrate="1000k"),
    ".mkv",
    "hevc",
    lambda: not NVENCC,
    is_rigaya=True,
)
_add(
    "nvencc_avc",
    NVEncCAVCSettings(preset="performance", bitrate="1000k"),
    ".mkv",
    "h264",
    lambda: not NVENCC,
    is_rigaya=True,
)
_add(
    "nvencc_av1",
    NVEncCAV1Settings(preset="performance", bitrate="1000k"),
    ".mkv",
    "av1",
    lambda: not NVENCC,
    is_rigaya=True,
)

# --- QSVEncC ---
_add(
    "qsvencc_hevc",
    QSVEncCSettings(preset="fastest", bitrate="1000k"),
    ".mkv",
    "hevc",
    lambda: not QSVENCC,
    is_rigaya=True,
)
_add(
    "qsvencc_avc",
    QSVEncCH264Settings(preset="fastest", bitrate="1000k"),
    ".mkv",
    "h264",
    lambda: not QSVENCC,
    is_rigaya=True,
)
_add(
    "qsvencc_av1",
    QSVEncCAV1Settings(preset="fastest", bitrate="1000k"),
    ".mkv",
    "av1",
    lambda: not QSVENCC,
    is_rigaya=True,
)

# --- VCEEncC ---
_add(
    "vceencc_hevc",
    VCEEncCSettings(preset="fast", bitrate="1000k"),
    ".mkv",
    "hevc",
    lambda: not VCEENCC,
    is_rigaya=True,
)
_add(
    "vceencc_avc",
    VCEEncCAVCSettings(preset="fast", bitrate="1000k"),
    ".mkv",
    "h264",
    lambda: not VCEENCC,
    is_rigaya=True,
)
_add(
    "vceencc_av1",
    VCEEncCAV1Settings(preset="fast", bitrate="1000k"),
    ".mkv",
    "av1",
    lambda: not VCEENCC,
    is_rigaya=True,
)


# ===========================================================================
# Parameterized test
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", ENCODER_TESTS)
def test_encode(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    if ON_CI:
        pytest.skip("Skipped on CI")
    if _source_probe is None:
        pytest.skip("Could not probe test source video")

    output_path = tmp_path / f"output_{encoder_id}{output_ext}"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_real_fastflix(settings, output_path, work_path, is_rigaya=is_rigaya)

    # Import and call the encoder's build()
    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)

    assert commands, f"Encoder {encoder_id} returned no commands"

    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)
