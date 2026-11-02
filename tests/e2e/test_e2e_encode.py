# -*- coding: utf-8 -*-
"""
E2E encode tests — build real commands, run real FFmpeg/Rigaya encodes, verify output.

Run locally:
    uv run pytest tests/e2e -v
    uv run pytest tests/e2e -v -k "x265"
    SKIP_NVIDIA=1 uv run pytest tests/e2e -v

Skipped on CI (GitHub Actions sets CI=true).
"""

import json
import subprocess

import pytest

from tests.e2e.conftest import (
    ALL_ENCODERS,
    FFMPEG,
    FFMPEG_ENCODERS,
    FFPROBE,
    LOSSLESS_ENCODERS,
    MEDIA_DIR,
    NVENCC,
    ON_CI,
    SKIP_NVIDIA,
    SOURCES,
    create_fastflix,
    has_ffmpeg_encoder,
    make_params,
    run_commands,
    verify_lossless_quality,
    verify_output,
)
from fastflix.models.encode import NVEncCSettings, x264Settings

pytestmark = [pytest.mark.e2e]

if ON_CI:
    pytestmark.append(pytest.mark.skip(reason="E2E tests skipped on CI"))
if not FFMPEG or not FFPROBE:
    pytestmark.append(pytest.mark.skip(reason="ffmpeg/ffprobe not found"))


# ===========================================================================
# Test 1: Basic encode — every encoder x HDR10+ source
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(ALL_ENCODERS))
def test_encode_basic(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """Every encoder can encode the HDR10+ test source."""
    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"basic_{encoder_id}{output_ext}"
    work_path = tmp_path / "work"
    work_path.mkdir()

    # copy encoder uses source codec — HDR10+ source is HEVC
    if encoder_id == "copy":
        expected_codec = "hevc"

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands, f"Encoder {encoder_id} returned no commands"

    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)


# ===========================================================================
# Test 2: Attachments — FFmpeg encoders x MKV source with fonts/cover
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(FFMPEG_ENCODERS))
def test_encode_with_attachments(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """FFmpeg encoders preserve font attachments and cover when encoding MKV."""
    source = SOURCES["attachments"]
    if not source.exists():
        pytest.skip("Attachment test source not found")

    # copy encoder: source is h264
    if encoder_id == "copy":
        expected_codec = "h264"

    output_path = tmp_path / f"attach_{encoder_id}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    data = verify_output(output_path, expected_codec)

    # Check font attachment preserved with mimetype
    attachments = [s for s in data["streams"] if s["codec_type"] == "attachment"]
    font_attachments = [s for s in attachments if s.get("tags", {}).get("mimetype") == "application/x-truetype-font"]
    assert len(font_attachments) >= 1, f"Font attachment missing. Found: {attachments}"

    # Check cover image preserved
    covers = [
        s
        for s in data["streams"]
        if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic", 0) == 1
    ]
    assert len(covers) >= 1, f"Cover image missing. Streams: {[s['codec_type'] for s in data['streams']]}"


# ===========================================================================
# Test 3: Data streams excluded for MKV output
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(FFMPEG_ENCODERS))
def test_encode_data_excluded_for_mkv(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """Data streams from MP4 source are excluded when encoding to MKV."""
    source = SOURCES["chapters"]
    if not source.exists():
        pytest.skip("Chapters test source not found")

    if encoder_id == "copy":
        expected_codec = "h264"

    output_path = tmp_path / f"nodata_{encoder_id}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    # Verify -dn is in the final command (multi-pass encoders have it in the last pass)
    final_cmd_str = commands[-1].to_string()
    assert "-dn" in final_cmd_str, f"Expected -dn to exclude data streams for MKV: {final_cmd_str}"

    run_commands(commands, work_path)
    data = verify_output(output_path, expected_codec)

    # No data streams in output
    out_data = [s for s in data["streams"] if s["codec_type"] == "data"]
    assert len(out_data) == 0, f"Data streams should be excluded from MKV. Found: {out_data}"


# ===========================================================================
# Test 4: Data streams mapped for MP4 output
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(FFMPEG_ENCODERS))
def test_encode_data_mapped_for_mp4(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """Data streams from MP4 source are mapped (not excluded) when encoding to MP4."""
    source = SOURCES["chapters"]
    if not source.exists():
        pytest.skip("Chapters test source not found")

    # Skip encoders that can't output MP4
    if encoder_id in ("vp9", "vvc"):
        pytest.skip(f"{encoder_id} doesn't typically output MP4")
    if encoder_id == "copy":
        expected_codec = "h264"

    output_path = tmp_path / f"data_{encoder_id}.mp4"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    # Verify the final command maps the data stream and sets title/handler metadata
    final_cmd_str = commands[-1].to_string()
    assert "-map 0:2" in final_cmd_str, f"Data stream should be mapped for MP4: {final_cmd_str}"
    assert "-c:d copy" in final_cmd_str, f"Data stream should use copy codec: {final_cmd_str}"
    assert "title=" in final_cmd_str, f"Data track should have title metadata: {final_cmd_str}"
    assert "handler=" in final_cmd_str, f"Data track should have handler metadata: {final_cmd_str}"
    assert "-dn" not in final_cmd_str, f"Should NOT have -dn when data is mapped: {final_cmd_str}"

    # Encode must succeed (even if FFmpeg silently drops the data stream)
    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)


# ===========================================================================
# Test 5: "Same as Source" extension — MKV source → .mkv output
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(FFMPEG_ENCODERS))
def test_encode_same_as_source_mkv(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """'Same as Source' with MKV source resolves to .mkv output."""
    source = SOURCES["attachments"]  # MKV source
    if not source.exists():
        pytest.skip("Attachment MKV test source not found")

    if encoder_id == "copy":
        expected_codec = "h264"

    # Use .mkv extension (simulating "Same as Source" resolution for MKV input)
    output_path = tmp_path / f"same_mkv_{encoder_id}.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
    )

    # Verify the resolved extension matches source
    assert source.suffix.lower() == ".mkv"
    assert output_path.suffix.lower() == ".mkv"

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)


# ===========================================================================
# Test 6: "Same as Source" extension — MP4 source → .mp4 output
# ===========================================================================
@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(FFMPEG_ENCODERS))
def test_encode_same_as_source_mp4(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """'Same as Source' with MP4 source resolves to .mp4 output."""
    source = SOURCES["chapters"]  # MP4 source
    if not source.exists():
        pytest.skip("Chapters MP4 test source not found")

    # Skip encoders that can't output MP4
    if encoder_id in ("vp9", "vvc"):
        pytest.skip(f"{encoder_id} doesn't typically output MP4")
    if encoder_id == "copy":
        expected_codec = "h264"

    # Use .mp4 extension (simulating "Same as Source" resolution for MP4 input)
    output_path = tmp_path / f"same_mp4_{encoder_id}.mp4"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
    )

    # Verify the resolved extension matches source
    assert source.suffix.lower() == ".mp4"
    assert output_path.suffix.lower() == ".mp4"

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands

    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)


# ===========================================================================
# Test 7: Subtitle disposition flags in encode output
# ===========================================================================
def test_encode_subtitle_default_disposition(tmp_path):
    """Encode MKV with subtitles, verify default disposition flag appears in command."""
    source = SOURCES["attachments"]  # MKV with ASS subtitle
    if not source.exists():
        pytest.skip("Attachment MKV test source not found")

    output_path = tmp_path / "sub_disp.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    from fastflix.models.encode import x265Settings

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=x265Settings(preset="ultrafast", crf=51),
        output_path=output_path,
        work_path=work_path,
        include_subtitles=True,
    )

    # Set default disposition on first subtitle (simulating "first" profile mode)
    assert len(fastflix.current_video.subtitle_tracks) >= 1, "Source should have subtitles"
    fastflix.current_video.subtitle_tracks[0].dispositions["default"] = True

    from fastflix.encoders.hevc_x265 import command_builder

    commands = command_builder.build(fastflix)
    assert commands

    # Final command should contain disposition with "default"
    final_cmd = commands[-1].to_string()
    assert "-disposition:" in final_cmd, f"Expected disposition flag in command: {final_cmd}"
    assert "default" in final_cmd, f"Expected 'default' disposition: {final_cmd}"

    run_commands(commands, work_path)
    data = verify_output(output_path, "hevc")

    # Verify subtitle stream exists in output
    out_subs = [s for s in data["streams"] if s["codec_type"] == "subtitle"]
    assert len(out_subs) >= 1, f"Subtitle should be in output. Streams: {[s['codec_type'] for s in data['streams']]}"


# ===========================================================================
# Test 8: AOM AV1 2-pass CRF encode
# ===========================================================================
def test_encode_aom_av1_two_pass_crf(tmp_path):
    """AOM AV1 2-pass CRF produces two commands and encodes successfully."""
    if not has_ffmpeg_encoder("libaom-av1"):
        pytest.skip("libaom-av1 not available")

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / "aom_2pass_crf.mkv"
    work_path = tmp_path / "work"
    work_path.mkdir()

    from fastflix.models.encode import AOMAV1Settings

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=AOMAV1Settings(cpu_used="8", usage="realtime", crf=63, single_pass=False),
        output_path=output_path,
        work_path=work_path,
        include_data=False,
        include_attachments=False,
    )

    from fastflix.encoders.av1_aom import command_builder

    commands = command_builder.build(fastflix)
    assert len(commands) == 2, f"Expected 2-pass (2 commands), got {len(commands)}"
    assert "First Pass CRF" in commands[0].name
    assert "Second Pass CRF" in commands[1].name

    # Verify pass flags in commands
    cmd1_str = commands[0].to_string()
    cmd2_str = commands[1].to_string()
    assert "-pass 1" in cmd1_str
    assert "-pass 2" in cmd2_str
    assert "-crf 63" in cmd1_str
    assert "-crf 63" in cmd2_str

    run_commands(commands, work_path)
    verify_output(output_path, "av1")


# ===========================================================================
# Test 9: Lossless command flags — verify lossless flag in generated commands
# ===========================================================================
# Rate control flags that must NOT appear in lossless commands (per encoder)
_LOSSLESS_FORBIDDEN_FLAGS = {
    "hevc_x265": ["-crf:v", "-b:v"],
    "avc_x264": ["-crf:v", "-b:v"],
    "av1_aom": ["-crf", "-b:v"],
    "vp9": ["-crf:v", "-b:v"],
    "svt_av1": ["-crf", "-qp", "-b:v"],
    "webp": [],  # WebP has its own quality model, no CRF/bitrate flags to check
}


@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(LOSSLESS_ENCODERS))
def test_lossless_command_flags(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """Lossless encoders include the lossless flag and exclude rate control flags."""
    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"lossless_{encoder_id}{output_ext}"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands, f"Encoder {encoder_id} returned no commands"

    # Verify lossless flag is present in at least one command
    all_cmd_str = " ".join(cmd.to_string() for cmd in commands)
    assert "lossless" in all_cmd_str.lower(), f"Expected 'lossless' in command for {encoder_id}: {all_cmd_str}"

    # Verify rate control flags are NOT present — lossless must skip CRF/bitrate/QP
    for flag in _LOSSLESS_FORBIDDEN_FLAGS.get(encoder_id, []):
        for cmd in commands:
            cmd_list = cmd.to_list()
            assert flag not in cmd_list, (
                f"Lossless {encoder_id} must not include '{flag}' in command: {cmd.to_string()}"
            )


# ===========================================================================
# Test 10: Lossless encode — full encode with framemd5 quality verification
# ===========================================================================
# Encoders confirmed to produce bit-exact lossless output with 10-bit HDR content
BIT_EXACT_LOSSLESS = {"hevc_x265", "avc_x264", "vp9"}


@pytest.mark.parametrize("encoder_id,settings,output_ext,expected_codec,is_rigaya", make_params(LOSSLESS_ENCODERS))
def test_lossless_encode(encoder_id, settings, output_ext, expected_codec, is_rigaya, tmp_path):
    """Lossless encoders produce valid output with zero quality loss."""
    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    output_path = tmp_path / f"lossless_{encoder_id}{output_ext}"
    work_path = tmp_path / "work"
    work_path.mkdir()

    fastflix = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output_path,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )

    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    commands = module.build(fastflix)
    assert commands, f"Encoder {encoder_id} returned no commands"

    run_commands(commands, work_path)
    verify_output(output_path, expected_codec)

    # Verify true lossless via per-frame MD5 comparison for bit-exact encoders
    if encoder_id in BIT_EXACT_LOSSLESS:
        verify_lossless_quality(source, output_path)


# ===========================================================================
# Filter E2E test helpers
# ===========================================================================


def sample_positions_5(h, w):
    return [
        (h // 4, w // 4),
        (h // 4, 3 * w // 4),
        (h // 2, w // 2),
        (3 * h // 4, w // 4),
        (3 * h // 4, 3 * w // 4),
    ]


def _get_frame_rgb(video_path):
    """Decode first frame to raw RGB24 bytes, returning (pixels, width, height)."""
    probe = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", str(video_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    data = json.loads(probe.stdout)
    vs = [s for s in data["streams"] if s["codec_type"] == "video"][0]
    w, h = int(vs["width"]), int(vs["height"])

    result = subprocess.run(
        [FFMPEG, "-i", str(video_path), "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Failed to decode {video_path}"
    assert len(result.stdout) >= w * h * 3
    return result.stdout, w, h


def _avg_rgb(pixels, w, h):
    """Compute average R, G, B across the entire frame."""
    r_sum = g_sum = b_sum = 0
    count = w * h
    for i in range(0, count * 3, 3):
        r_sum += pixels[i]
        g_sum += pixels[i + 1]
        b_sum += pixels[i + 2]
    return r_sum / count, g_sum / count, b_sum / count


def _avg_luma(pixels, w, h):
    """Approximate average luma (BT.601) across the frame."""
    total = 0.0
    count = w * h
    for i in range(0, count * 3, 3):
        total += 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2]
    return total / count


def _encode_pair(tmp_path, apply_filter, encoder_id="avc_x264", is_rigaya=False):
    """Encode the HDR10+ source twice: once baseline, once with apply_filter applied.

    Returns (baseline_pixels, filtered_pixels, width, height).
    """
    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    if is_rigaya:
        settings = NVEncCSettings(preset="performance", bitrate="1000k")
        module_path = f"fastflix.encoders.{encoder_id}.command_builder"
        expected_codec = "hevc"
    else:
        settings = x264Settings(preset="ultrafast", crf=28, pix_fmt="yuv420p")
        module_path = f"fastflix.encoders.{encoder_id}.command_builder"
        expected_codec = "h264"

    module = __import__(module_path, fromlist=["build"])
    work_path = tmp_path / "work"
    work_path.mkdir(exist_ok=True)

    # Baseline
    out_base = tmp_path / "baseline.mkv"
    ff_base = create_fastflix(
        source_path=source,
        encoder_settings=settings.model_copy(),
        output_path=out_base,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )
    run_commands(module.build(ff_base), work_path)
    verify_output(out_base, expected_codec)

    # Filtered
    out_filt = tmp_path / "filtered.mkv"
    ff_filt = create_fastflix(
        source_path=source,
        encoder_settings=settings.model_copy(),
        output_path=out_filt,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )
    apply_filter(ff_filt)
    run_commands(module.build(ff_filt), work_path)
    verify_output(out_filt, expected_codec)

    base_px, w, h = _get_frame_rgb(out_base)
    filt_px, _, _ = _get_frame_rgb(out_filt)
    return base_px, filt_px, w, h


# ===========================================================================
# Filter tests: Brightness
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,is_rigaya",
    [
        pytest.param(
            "avc_x264",
            False,
            id="x264",
            marks=pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available"),
        ),
        pytest.param(
            "nvencc_hevc",
            True,
            id="nvencc",
            marks=pytest.mark.skipif(not NVENCC or SKIP_NVIDIA, reason="NVEncC not available"),
        ),
    ],
)
def test_filter_brightness(encoder_id, is_rigaya, tmp_path):
    """Positive brightness makes pixels brighter (higher luma)."""
    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "brightness", "0.3"),
        encoder_id=encoder_id,
        is_rigaya=is_rigaya,
    )
    base_luma = _avg_luma(base_px, w, h)
    filt_luma = _avg_luma(filt_px, w, h)
    assert filt_luma > base_luma + 5, (
        f"Brightness filter should increase luma: base={base_luma:.1f}, filtered={filt_luma:.1f}"
    )


# ===========================================================================
# Filter tests: Vibrance (FFmpeg only — ʘ)
# ===========================================================================
@pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available")
def test_filter_vibrance(tmp_path):
    """Positive vibrance increases color saturation (R-B spread widens for colorful pixels)."""
    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "vibrance", "2.0"),
    )

    # Saturation proxy: average absolute difference between max and min channel per pixel
    def avg_saturation(pixels, w, h):
        total = 0.0
        count = w * h
        for i in range(0, count * 3, 3):
            total += max(pixels[i], pixels[i + 1], pixels[i + 2]) - min(pixels[i], pixels[i + 1], pixels[i + 2])
        return total / count

    base_sat = avg_saturation(base_px, w, h)
    filt_sat = avg_saturation(filt_px, w, h)
    assert filt_sat > base_sat + 1, f"Vibrance should increase saturation: base={base_sat:.1f}, filtered={filt_sat:.1f}"


# ===========================================================================
# Filter tests: Color Temperature (FFmpeg only — ʘ)
# ===========================================================================
@pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available")
def test_filter_color_temperature(tmp_path):
    """Warm color temperature (low Kelvin) shifts pixels toward red, away from blue."""
    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "color_temperature", "2000"),
    )
    base_r, _, base_b = _avg_rgb(base_px, w, h)
    filt_r, _, filt_b = _avg_rgb(filt_px, w, h)
    # Warm temp: R should increase relative to B
    base_rb_diff = base_r - base_b
    filt_rb_diff = filt_r - filt_b
    assert filt_rb_diff > base_rb_diff + 3, (
        f"Warm color temp should shift R-B balance warmer: base R-B={base_rb_diff:.1f}, filtered R-B={filt_rb_diff:.1f}"
    )


# ===========================================================================
# Filter tests: Curves Preset
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,is_rigaya",
    [
        pytest.param(
            "avc_x264",
            False,
            id="x264",
            marks=pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available"),
        ),
        pytest.param(
            "nvencc_hevc",
            True,
            id="nvencc",
            marks=pytest.mark.skipif(not NVENCC or SKIP_NVIDIA, reason="NVEncC not available"),
        ),
    ],
)
def test_filter_curves_darker(encoder_id, is_rigaya, tmp_path):
    """Curves preset 'darker' reduces average luma."""
    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "curves_preset", "darker"),
        encoder_id=encoder_id,
        is_rigaya=is_rigaya,
    )
    base_luma = _avg_luma(base_px, w, h)
    filt_luma = _avg_luma(filt_px, w, h)
    assert filt_luma < base_luma - 3, (
        f"Curves 'darker' should reduce luma: base={base_luma:.1f}, filtered={filt_luma:.1f}"
    )


# ===========================================================================
# Filter tests: Colorbalance (FFmpeg only — ʘ)
# ===========================================================================
@pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available")
def test_filter_colorbalance_warm_shadows(tmp_path):
    """Warm Shadows colorbalance shifts R higher in dark pixel regions."""
    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "colorbalance", "colorbalance=rs=0.15:bs=-0.15"),
    )
    # Average R channel in dark pixels (luma < 80) should increase
    base_r_sum = filt_r_sum = 0
    total_dark = 0
    for i in range(0, w * h * 3, 3):
        luma = 0.299 * base_px[i] + 0.587 * base_px[i + 1] + 0.114 * base_px[i + 2]
        if luma < 80:
            total_dark += 1
            base_r_sum += base_px[i]
            filt_r_sum += filt_px[i]
    assert total_dark > 0, "No dark pixels found in source"
    base_avg_r = base_r_sum / total_dark
    filt_avg_r = filt_r_sum / total_dark
    assert filt_avg_r > base_avg_r + 1, (
        f"Warm Shadows should boost average R in dark pixels: base={base_avg_r:.1f}, filtered={filt_avg_r:.1f}"
    )


# ===========================================================================
# Filter tests: Unsharp Mask
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,is_rigaya",
    [
        pytest.param(
            "avc_x264",
            False,
            id="x264",
            marks=pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available"),
        ),
        pytest.param(
            "nvencc_hevc",
            True,
            id="nvencc",
            marks=pytest.mark.skipif(not NVENCC or SKIP_NVIDIA, reason="NVEncC not available"),
        ),
    ],
)
def test_filter_unsharp(encoder_id, is_rigaya, tmp_path):
    """Unsharp mask increases local contrast (pixel variance increases)."""
    from fastflix.widgets.panels.advanced_panel import unsharp_presets

    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "unsharp", unsharp_presets["strong"]),
        encoder_id=encoder_id,
        is_rigaya=is_rigaya,
    )

    # Measure local contrast: average absolute difference between adjacent pixels
    def local_contrast(pixels, w, h):
        total = 0.0
        count = 0
        for row in range(h):
            for col in range(w - 1):
                i = (row * w + col) * 3
                j = i + 3
                total += abs(pixels[i] - pixels[j])  # R channel neighbor diff
                count += 1
        return total / count if count else 0

    base_contrast = local_contrast(base_px, w, h)
    filt_contrast = local_contrast(filt_px, w, h)
    assert filt_contrast > base_contrast, (
        f"Unsharp should increase local contrast: base={base_contrast:.2f}, filtered={filt_contrast:.2f}"
    )


# ===========================================================================
# Filter tests: Deflicker (FFmpeg only — ʘ)
# ===========================================================================
@pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available")
def test_filter_deflicker(tmp_path):
    """Deflicker encodes successfully (temporal effect — verify encode completes)."""
    from fastflix.widgets.panels.advanced_panel import deflicker_presets

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    work_path = tmp_path / "work"
    work_path.mkdir()
    output = tmp_path / "deflicker.mkv"

    ff = create_fastflix(
        source_path=source,
        encoder_settings=x264Settings(preset="ultrafast", crf=28, pix_fmt="yuv420p"),
        output_path=output,
        work_path=work_path,
        include_data=False,
        include_attachments=False,
    )
    ff.current_video.video_settings.deflicker = deflicker_presets["medium"]
    module = __import__("fastflix.encoders.avc_x264.command_builder", fromlist=["build"])
    commands = module.build(ff)
    cmd_str = commands[0].to_string()
    assert "deflicker" in cmd_str, f"deflicker filter not in command: {cmd_str}"
    run_commands(commands, work_path)
    verify_output(output, "h264")


# ===========================================================================
# Filter tests: Pad / Letterbox
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,is_rigaya",
    [
        pytest.param(
            "avc_x264",
            False,
            id="x264",
            marks=pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available"),
        ),
        pytest.param(
            "nvencc_hevc",
            True,
            id="nvencc",
            marks=pytest.mark.skipif(not NVENCC or SKIP_NVIDIA, reason="NVEncC not available"),
        ),
    ],
)
def test_filter_pad_letterbox(encoder_id, is_rigaya, tmp_path):
    """Pad to 1:1 adds black bars — border pixels should be near-black."""

    def apply_pad(ff):
        ff.current_video.video_settings.pad_aspect = "1:1"
        ff.current_video.video_settings.pad_color = "black"

    source = SOURCES["hdr10plus"]
    if not source.exists():
        pytest.skip("HDR10+ test source not found")

    if is_rigaya:
        settings = NVEncCSettings(preset="performance", bitrate="1000k")
        expected_codec = "hevc"
    else:
        settings = x264Settings(preset="ultrafast", crf=28, pix_fmt="yuv420p")
        expected_codec = "h264"

    work_path = tmp_path / "work"
    work_path.mkdir()
    output = tmp_path / "padded.mkv"

    ff = create_fastflix(
        source_path=source,
        encoder_settings=settings,
        output_path=output,
        work_path=work_path,
        is_rigaya=is_rigaya,
        include_data=False,
        include_attachments=False,
    )
    apply_pad(ff)
    module = __import__(f"fastflix.encoders.{encoder_id}.command_builder", fromlist=["build"])
    run_commands(module.build(ff), work_path)
    verify_output(output, expected_codec)

    pixels, w, h = _get_frame_rgb(output)

    # For 1:1 pad on a wider-than-tall source, black bars appear at top/bottom.
    # For a taller-than-wide source, black bars at left/right.
    # Either way, some border pixels should be near-black.
    # Check top-left and bottom-right corner pixels.
    corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
    black_corners = 0
    for row, col in corners:
        off = (row * w + col) * 3
        r, g, b = pixels[off], pixels[off + 1], pixels[off + 2]
        if r < 20 and g < 20 and b < 20:
            black_corners += 1
    assert black_corners >= 2, (
        f"Pad to 1:1 should produce black bars — expected at least 2 near-black corners, got {black_corners}"
    )


# ===========================================================================
# Filter tests: LUT3D
# ===========================================================================
@pytest.mark.parametrize(
    "encoder_id,is_rigaya",
    [
        pytest.param(
            "avc_x264",
            False,
            id="x264",
            marks=pytest.mark.skipif(not has_ffmpeg_encoder("libx264"), reason="libx264 not available"),
        ),
    ],
)
def test_filter_lut3d(encoder_id, is_rigaya, tmp_path):
    """LUT3D with R/B swap produces pixels with swapped red and blue channels."""
    lut_path = MEDIA_DIR / "test_color_shift.cube"
    assert lut_path.exists(), f"Test LUT not found: {lut_path}"

    base_px, filt_px, w, h = _encode_pair(
        tmp_path,
        lambda ff: setattr(ff.current_video.video_settings, "lut3d_path", str(lut_path)),
        encoder_id=encoder_id,
        is_rigaya=is_rigaya,
    )

    tolerance = 30
    swap_confirmed = 0
    for row, col in sample_positions_5(h, w):
        off = (row * w + col) * 3
        r_orig, g_orig, b_orig = base_px[off], base_px[off + 1], base_px[off + 2]
        r_lut, g_lut, b_lut = filt_px[off], filt_px[off + 1], filt_px[off + 2]
        if abs(r_lut - b_orig) <= tolerance and abs(b_lut - r_orig) <= tolerance and abs(g_lut - g_orig) <= tolerance:
            swap_confirmed += 1

    assert swap_confirmed >= 3, f"LUT3D R/B swap not detected: only {swap_confirmed}/5 sample points matched"
