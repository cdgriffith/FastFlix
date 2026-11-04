# -*- coding: utf-8 -*-
"""#743: .mov sources with a tmcd timecode track failed to encode to .mp4."""

from pathlib import Path

import pytest

from fastflix.encoders.common.helpers import generate_ending
from fastflix.models.encode import DataTrack

AUDIO = ["-map", "0:1", "-c:a", "copy"]


def _tmcd(enabled=True, timecode="01:00:00:00"):
    return DataTrack(
        index=2,
        outdex=2,
        enabled=enabled,
        codec_name="",  # ffprobe JSON omits codec_name for tmcd
        codec_type="data",
        raw_info={"codec_tag_string": "tmcd", "tags": {"timecode": timecode}},
    )


def _unknown_meta():
    return DataTrack(
        index=3, outdex=3, enabled=True, codec_name="none", codec_type="data", raw_info={"codec_tag_string": "mett"}
    )


def _bin_data():
    return DataTrack(index=4, outdex=4, enabled=True, codec_name="bin_data", codec_type="data")


@pytest.mark.parametrize("ext", ["mp4", "m4v"])
def test_tmcd_becomes_timecode_for_mp4(ext):
    ending, _ = generate_ending(
        audio=AUDIO, subtitles=[], output_video=Path(f"output.{ext}"), data_tracks=[_tmcd(), _unknown_meta()]
    )
    assert "0:2" not in ending and "0:3" not in ending
    assert "-c:d" not in ending
    assert ending[ending.index("-timecode") + 1] == "01:00:00:00"
    assert ending.index("-timecode") < ending.index(f"output.{ext}")


def test_disabled_tmcd_drops_timecode():
    ending, _ = generate_ending(
        audio=AUDIO, subtitles=[], output_video=Path("output.mp4"), data_tracks=[_tmcd(enabled=False)]
    )
    assert "-timecode" not in ending


def test_tmcd_still_copied_for_mov():
    ending, _ = generate_ending(audio=AUDIO, subtitles=[], output_video=Path("output.mov"), data_tracks=[_tmcd()])
    assert "0:2" in ending
    assert "-c:d" in ending
    assert "-timecode" not in ending


def test_known_data_codec_still_copied_for_mp4():
    ending, _ = generate_ending(audio=AUDIO, subtitles=[], output_video=Path("output.mp4"), data_tracks=[_bin_data()])
    assert "0:4" in ending
    assert "-c:d" in ending


def test_mp4_copyable():
    assert not _tmcd().mp4_copyable()
    assert _tmcd().is_timecode()
    assert not _unknown_meta().mp4_copyable()
    assert _bin_data().mp4_copyable()
    assert DataTrack(index=5, outdex=5, codec_name="ttf", codec_type="attachment").mp4_copyable()
