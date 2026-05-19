#!/usr/bin/env python
"""
Investigation script: verify which encoders produce truly bit-exact lossless output.

Run: uv run python tests/e2e/test_lossless_investigation.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
MEDIA_DIR = Path(__file__).parent.parent / "media"
HDR_SOURCE = MEDIA_DIR / "Beverly Hills Duck Pond - HDR10plus - Jessica Payne.mp4"


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def get_pix_fmt(path):
    r = run([FFPROBE, "-v", "quiet", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(path)])
    return r.stdout.strip().split("\n")[0].strip().rstrip(",")


def get_framemd5(path, pix_fmt=None, to=None):
    cmd = [FFMPEG]
    if to:
        cmd += ["-to", str(to)]
    cmd += ["-i", str(path), "-map", "0:v"]
    if pix_fmt:
        cmd += ["-pix_fmt", pix_fmt]
    cmd += ["-f", "framemd5", "-"]
    r = run(cmd)
    return [line for line in r.stdout.splitlines() if line and not line.startswith("#")]


def get_psnr(path1, path2, to1=None, to2=None):
    cmd = [FFMPEG]
    if to1:
        cmd += ["-to", str(to1)]
    cmd += ["-i", str(path1)]
    if to2:
        cmd += ["-to", str(to2)]
    cmd += ["-i", str(path2), "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"]
    r = run(cmd)
    for line in r.stderr.splitlines():
        if "average:" in line and "PSNR" in line:
            return line
    return f"PSNR not found in: {r.stderr[-500:]}"


def compare_framemd5(frames_a, frames_b):
    if len(frames_a) != len(frames_b):
        return f"Frame count mismatch: {len(frames_a)} vs {len(frames_b)}"
    mismatched = 0
    for a, b in zip(frames_a, frames_b):
        md5_a = a.split(",")[-1].strip()
        md5_b = b.split(",")[-1].strip()
        if md5_a != md5_b:
            mismatched += 1
    if mismatched == 0:
        return "EXACT MATCH (all frames identical)"
    return f"MISMATCH: {mismatched}/{len(frames_a)} frames differ"


def test_encoder(name, encode_cmd, source, tmp_dir, end_time=2):
    """Test a single encoder's lossless mode."""
    output = tmp_dir / f"lossless_{name}.mkv"
    cmd = [FFMPEG, "-y", "-to", str(end_time), "-i", str(source)] + encode_cmd + [str(output)]
    r = run(cmd)
    if r.returncode != 0:
        return {"status": "ENCODE FAILED", "error": r.stderr[-500:]}

    src_fmt = get_pix_fmt(source)
    out_fmt = get_pix_fmt(output)

    results = {
        "status": "OK",
        "source_pix_fmt": src_fmt,
        "output_pix_fmt": out_fmt,
    }

    # Test 1: Direct framemd5 comparison (native pixel formats)
    src_frames = get_framemd5(source, to=end_time)
    out_frames = get_framemd5(output)
    results["native_comparison"] = compare_framemd5(src_frames, out_frames)

    # Test 2: Force both to same pix_fmt (source's format)
    src_frames_forced = get_framemd5(source, pix_fmt=src_fmt, to=end_time)
    out_frames_forced = get_framemd5(output, pix_fmt=src_fmt)
    results["forced_src_fmt"] = compare_framemd5(src_frames_forced, out_frames_forced)

    # Test 3: Force both to output's pix_fmt
    if src_fmt != out_fmt:
        src_frames_out_fmt = get_framemd5(source, pix_fmt=out_fmt, to=end_time)
        out_frames_out_fmt = get_framemd5(output, pix_fmt=out_fmt)
        results["forced_out_fmt"] = compare_framemd5(src_frames_out_fmt, out_frames_out_fmt)

    # Test 4: Round-trip (re-encode output losslessly, compare decoded frames)
    reencoded = tmp_dir / f"reencoded_{name}.mkv"
    re_cmd = [FFMPEG, "-y", "-i", str(output)] + encode_cmd + [str(reencoded)]
    r2 = run(re_cmd)
    if r2.returncode == 0:
        out1_frames = get_framemd5(output)
        out2_frames = get_framemd5(reencoded)
        results["round_trip"] = compare_framemd5(out1_frames, out2_frames)
    else:
        results["round_trip"] = f"RE-ENCODE FAILED: {r2.stderr[-200:]}"

    # Test 5: PSNR (for reference)
    psnr_line = get_psnr(source, output, to1=end_time)
    results["psnr"] = psnr_line.strip() if psnr_line else "N/A"

    return results


def main():
    tmp_dir = Path(tempfile.mkdtemp())
    print(f"Working in: {tmp_dir}\n")

    # Create a simple synthetic 8-bit test source (avoids HDR/color issues)
    synth_source = tmp_dir / "synth.mkv"
    run(
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(synth_source),
        ]
    )
    synth_fmt = get_pix_fmt(synth_source)

    # Define all lossless encoder configurations to test
    encoders = {
        # (name, encode_args, source, end_time)
        "x265_synth": (
            ["-map", "0:v", "-c:v", "libx265", "-x265-params", "lossless=1", "-preset", "ultrafast", "-an"],
            synth_source,
            1,
        ),
        "x264_synth": (
            ["-map", "0:v", "-c:v", "libx264", "-x264-params", "lossless=1", "-preset", "ultrafast", "-an"],
            synth_source,
            1,
        ),
        "vp9_synth": (
            ["-map", "0:v", "-c:v", "libvpx-vp9", "-lossless", "1", "-an"],
            synth_source,
            1,
        ),
        "aom_synth": (
            ["-map", "0:v", "-c:v", "libaom-av1", "-lossless", "1", "-cpu-used", "8", "-an"],
            synth_source,
            1,
        ),
        "aom_synth_usage_good": (
            ["-map", "0:v", "-c:v", "libaom-av1", "-lossless", "1", "-cpu-used", "8", "-usage", "good", "-an"],
            synth_source,
            1,
        ),
        "aom_synth_via_params": (
            ["-map", "0:v", "-c:v", "libaom-av1", "-aom-params", "lossless=1", "-cpu-used", "8", "-an"],
            synth_source,
            1,
        ),
        "svt_synth": (
            ["-map", "0:v", "-c:v", "libsvtav1", "-svtav1-params", "lossless=1", "-preset", "13", "-an"],
            synth_source,
            1,
        ),
    }

    # Also test with the real HDR10+ source if available
    if HDR_SOURCE.exists():
        hdr_fmt = get_pix_fmt(HDR_SOURCE)
        print(f"HDR source pixel format: {hdr_fmt}\n")
        encoders.update(
            {
                "x265_hdr": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libx265",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-x265-params",
                        "lossless=1",
                        "-preset",
                        "ultrafast",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "x264_hdr_10bit": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-x264-params",
                        "lossless=1",
                        "-preset",
                        "ultrafast",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "x264_hdr_8bit": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-x264-params",
                        "lossless=1",
                        "-preset",
                        "ultrafast",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "vp9_hdr": (
                    ["-map", "0:v", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p10le", "-lossless", "1", "-an"],
                    HDR_SOURCE,
                    2,
                ),
                "aom_hdr": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libaom-av1",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-lossless",
                        "1",
                        "-cpu-used",
                        "8",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "aom_hdr_no_crf": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libaom-av1",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-lossless",
                        "1",
                        "-cpu-used",
                        "8",
                        "-usage",
                        "good",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "aom_hdr_with_crf": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libaom-av1",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-lossless",
                        "1",
                        "-cpu-used",
                        "8",
                        "-crf",
                        "26",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
                "svt_hdr": (
                    [
                        "-map",
                        "0:v",
                        "-c:v",
                        "libsvtav1",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-svtav1-params",
                        "lossless=1",
                        "-preset",
                        "13",
                        "-an",
                    ],
                    HDR_SOURCE,
                    2,
                ),
            }
        )

    print(f"Synthetic source pixel format: {synth_fmt}")
    print(f"Testing {len(encoders)} encoder configurations...\n")
    print("=" * 80)

    for name, (encode_cmd, source, end_time) in sorted(encoders.items()):
        print(f"\n### {name}")
        results = test_encoder(name, encode_cmd, source, tmp_dir, end_time)

        if results["status"] != "OK":
            print(f"  STATUS: {results['status']}")
            print(f"  ERROR: {results.get('error', 'unknown')[:300]}")
            continue

        print(f"  Pixel format: {results['source_pix_fmt']} -> {results['output_pix_fmt']}")
        print(f"  Native framemd5:     {results['native_comparison']}")
        print(f"  Forced source fmt:   {results['forced_src_fmt']}")
        if "forced_out_fmt" in results:
            print(f"  Forced output fmt:   {results['forced_out_fmt']}")
        print(f"  Round-trip:          {results['round_trip']}")
        psnr_short = results["psnr"]
        if "average:" in psnr_short:
            # Extract just the key PSNR values
            import re

            m = re.search(r"PSNR y:([\d.]+|inf).*average:([\d.]+|inf)", psnr_short)
            if m:
                psnr_short = f"Y={m.group(1)} Average={m.group(2)}"
        print(f"  PSNR:                {psnr_short}")

    print("\n" + "=" * 80)
    print("DONE")


if __name__ == "__main__":
    main()
