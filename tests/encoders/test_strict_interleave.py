# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from fastflix.encoders.common.helpers import generate_ending
from fastflix.models.encode import DataTrack

AUDIO = ["-map", "0:1", "-c:a", "copy"]
SUBS = ["-map", "0:2", "-c:s", "copy"]


def _has_flag(ending):
    if "-max_interleave_delta" not in ending:
        return False
    index = ending.index("-max_interleave_delta")
    assert ending[index + 1] == "0"
    # Must be an output option, so it has to come before the output file
    assert index < ending.index("output.mkv")
    return True


def test_auto_on_with_only_video_and_audio():
    """Copied audio must not be flushed far ahead of the video."""
    ending, _ = generate_ending(audio=AUDIO, subtitles=[], output_video=Path("output.mkv"))
    assert _has_flag(ending)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"subtitles": SUBS},
        {"cover": ["-attach", "cover.jpg"]},
        {"copy_data": True},
        {"data_tracks": [DataTrack(index=3, outdex=2, codec_type="data", codec_name="bin_data", enabled=True)]},
    ],
)
def test_auto_off_with_sparse_streams(kwargs):
    """Sparse streams make max_interleave_delta 0 buffer in memory, so auto leaves FFmpeg's default."""
    kwargs.setdefault("subtitles", [])
    ending, _ = generate_ending(audio=AUDIO, output_video=Path("output.mkv"), **kwargs)
    assert not _has_flag(ending)


def test_auto_ignores_burned_in_subtitles():
    """Burn-in produces no subtitle -map, so nothing sparse is muxed."""
    ending, _ = generate_ending(
        audio=AUDIO, subtitles=["-default_mode", "infer_no_subs"], output_video=Path("output.mkv")
    )
    assert _has_flag(ending)


def test_always_and_never_override_auto():
    ending, _ = generate_ending(audio=AUDIO, subtitles=SUBS, output_video=Path("output.mkv"), strict_interleave=True)
    assert _has_flag(ending)
    ending, _ = generate_ending(audio=AUDIO, subtitles=[], output_video=Path("output.mkv"), strict_interleave=False)
    assert not _has_flag(ending)
