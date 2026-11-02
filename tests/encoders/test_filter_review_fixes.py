# -*- coding: utf-8 -*-
from pathlib import Path
from unittest import mock

import pytest
from box import Box

from fastflix.encoders.common.audio import audio_quality_converter, build_audio, channels_for_layout
from fastflix.encoders.common.helpers import (
    generate_all,
    generate_color_details,
    generate_ffmpeg_start,
    generate_filters,
    validate_ffmpeg_color,
)
from fastflix.encoders.common.subtitles import build_subtitle
from fastflix.models.encode import AudioTrack, SubtitleTrack, x265Settings


def _sub(index, outdex, kind="text", **kw):
    return SubtitleTrack(index=index, outdex=outdex, language="eng", subtitle_type=kind, **kw)


# ---- item 1: PGS burn-in
@pytest.mark.parametrize("kind", ["picture", "pgs"])
def test_bitmap_burn_in_uses_overlay(kind):
    result = generate_filters(
        selected_track=0, source=Path("in.mkv"), burn_in_subtitle_track=2, burn_in_subtitle_type=kind
    )
    assert "[0:0][0:2]overlay" in result[1]
    assert "subtitles=" not in result[1]


def test_text_burn_in_still_uses_subtitles_filter():
    result = generate_filters(
        selected_track=0, source=Path("in.mkv"), burn_in_subtitle_track=0, burn_in_subtitle_type="text"
    )
    assert "subtitles=" in result[1]


# ---- item 2: bitmap subs in MP4, default_mode gating
@pytest.mark.parametrize("kind", ["picture", "pgs"])
def test_mp4_drops_bitmap_tracks_and_shifts_outdex(kind):
    tracks = [_sub(3, 1, kind), _sub(4, 2, "text")]
    cmd, _, _ = build_subtitle(tracks, output_path="out.mp4")
    assert "0:3" not in cmd
    assert "0:4" in cmd
    assert "-c:1" in cmd and "-c:2" not in cmd
    assert "mov_text" in cmd


def test_mkv_keeps_bitmap_tracks_with_copy():
    cmd, _, _ = build_subtitle([_sub(3, 1, "pgs")], output_path="out.mkv")
    assert cmd[:4] == ["-map", "0:3", "-c:1", "copy"]


@pytest.mark.parametrize(
    "path,expected",
    [("out.mkv", True), ("out.webm", True), ("out.MKV", True), ("out.mp4", False), ("out.avi", False), (None, True)],
)
def test_default_mode_only_for_matroska(path, expected):
    cmd, _, _ = build_subtitle([], output_path=path)
    assert (cmd[-2:] == ["-default_mode", "infer_no_subs"]) is expected


# ---- item 3: burn-in index 0
def test_burn_in_track_zero_shifts_later_outdex():
    tracks = [_sub(0, 1, "text", burn_in=True), _sub(1, 2, "text")]
    cmd, burn, kind = build_subtitle(tracks, output_path="out.mkv")
    assert burn == 0 and kind == "text"
    assert "-c:1" in cmd and "-c:2" not in cmd


def test_external_burn_in_si_not_remapped_through_source_streams(fastflix_instance):
    fastflix_instance.current_video.streams["subtitle"] = [Box({"index": 3}), Box({"index": 0})]
    fastflix_instance.current_video.subtitle_tracks = [
        _sub(0, 1, "text", burn_in=True, external=True, file_path="/p/x.srt")
    ]
    fastflix_instance.current_video.video_settings.video_encoder_settings = x265Settings()
    with mock.patch("fastflix.encoders.common.helpers.build_subtitle") as bs:
        bs.return_value = ([], 0, "text")
        beginning, ending, _ = generate_all(fastflix_instance, "libx265")
    assert ":si=0" in " ".join(beginning)


# ---- item 4: audio
@pytest.mark.parametrize(
    "layout,count",
    [("5.1(side)", 6), ("5.1.2", 8), ("7.1.2", 10), ("7.1.4", 12), ("6.1(back)", 7), ("octagonal", 8), ("stereo", 2)],
)
def test_channels_for_layout_known(layout, count):
    assert channels_for_layout(layout, None) == count


def test_channels_for_layout_unknown_uses_channels_field():
    assert channels_for_layout("weird", 5) == 5
    assert channels_for_layout("", 3) == 3
    assert channels_for_layout("weird", None) is None


def _audio(raw, downmix=None, codec="aac", **kw):
    return AudioTrack(
        index=1,
        outdex=0,
        codec="dts",
        raw_info=Box(raw),
        conversion_codec=codec,
        conversion_bitrate="128k",
        downmix=downmix,
        **kw,
    )


def test_unknown_layout_does_not_force_stereo_or_raise():
    cmd = build_audio([_audio({"channel_layout": "7.1.4", "channels": 12})])
    assert "-c:0" in cmd
    assert not any("channel_layouts=stereo" in x for x in cmd)


def test_unknown_layout_skips_aformat():
    cmd = build_audio([_audio({"channel_layout": "mystery", "channels": 4})])
    assert not any("aformat" in x for x in cmd)


def test_missing_layout_skips_aformat():
    cmd = build_audio([_audio({"channels": 2})])
    assert not any("aformat" in x for x in cmd)


def test_downmix_still_sets_ac_and_aformat():
    cmd = build_audio([_audio({"channel_layout": "5.1", "channels": 6}, downmix="stereo")])
    assert "-ac:0" in cmd and "aformat=channel_layouts=stereo" in cmd


def test_known_layout_keeps_aformat():
    cmd = build_audio([_audio({"channel_layout": "5.1(side)", "channels": 6})])
    assert "aformat=channel_layouts=5.1(side)" in cmd


@pytest.mark.parametrize(
    "codec,quality,channels,expected",
    [
        ("ac3", 0, 6, "-b:1 640k"),
        ("ac3", 0, 2, "-b:1 640k"),
        ("ac3", 9, 2, "-b:1 64k"),
        ("eac3", 0, 8, "-b:1 3840k"),
        ("eac3", 0, 32, "-b:1 6144k"),
        ("libopus", 0, None, "-vbr:1 on -b:1 240k"),
        ("aac", 0, None, "-q:1 2"),
        ("ac3", 0, None, "-b:1 640k"),
    ],
)
def test_quality_converter_clamps_and_handles_none(codec, quality, channels, expected):
    assert audio_quality_converter(quality, codec, channels=channels, track_number=1) == expected


def test_build_audio_quality_path_with_none_channels():
    t = AudioTrack(
        index=1, outdex=0, raw_info=Box({"channel_layout": "stereo"}), conversion_codec="ac3", conversion_aq=0
    )
    t.raw_info = Box({"channel_layout": "stereo"})
    cmd = build_audio([t])
    assert "-b:0" in cmd


# ---- item 5: tonemap order
def test_tonemap_before_grading_and_overlay_after_tonemap():
    result = generate_filters(
        selected_track=0,
        source=Path("in.mkv"),
        remove_hdr=True,
        brightness="0.1",
        colorbalance="colorbalance=rs=0.1",
        curves_preset="vintage",
        lut3d_path="a.cube",
        sharpen="0.5",
        burn_in_subtitle_track=2,
        burn_in_subtitle_type="pgs",
    )
    fc = result[1]
    tm = fc.index("tonemap=tonemap")
    for token in ("eq=", "colorbalance", "curves=", "lut3d=", "cas="):
        assert tm < fc.index(token), token
    assert tm < fc.index("overlay")
    assert "[0:2]overlay" in fc


def test_denoise_before_tonemap_before_grading_without_subtitles():
    fc = generate_filters(
        selected_track=0, source=Path("in.mkv"), remove_hdr=True, denoise="hqdn3d", brightness="0.1", sharpen="0.5"
    )[1]
    assert fc.index("hqdn3d") < fc.index("tonemap=tonemap") < fc.index("eq=") < fc.index("cas=")


def test_tonemap_keeps_10bit_when_target_is_10bit():
    r = generate_filters(selected_track=0, source=Path("in.mkv"), remove_hdr=True, target_pix_fmt="yuv420p10le")
    assert r[1].endswith("format=yuv420p10le[v]")
    r = generate_filters(selected_track=0, source=Path("in.mkv"), remove_hdr=True, target_pix_fmt="yuv420p")
    assert r[1].endswith("format=yuv420p[v]")
    r = generate_filters(selected_track=0, source=Path("in.mkv"), remove_hdr=True)
    assert r[1].endswith("format=yuv420p[v]")


def test_opencl_and_vaapi_branches_unchanged():
    r = generate_filters(selected_track=0, source=Path("in.mkv"), remove_hdr=True, enable_opencl=True)
    assert "tonemap_opencl" in r[1]
    r = generate_filters(selected_track=0, source=Path("in.mkv"), remove_hdr=True, vaapi=True)
    assert "tonemap_vaapi" in r[1]


# ---- item 6: tag bt709 when tonemapping
def test_color_details_tag_bt709_when_tonemapping(fastflix_instance):
    fastflix_instance.current_video.video_settings.remove_hdr = True
    assert generate_color_details(fastflix_instance) == [
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
    ]


# ---- item 7
@pytest.mark.parametrize(
    "value", ["black", "white", "Red", "0xFF00AA", "#00ff00", "red@0.5", "0x00FF00@0xAA", "random"]
)
def test_pad_color_valid(value):
    assert validate_ffmpeg_color(value) == value


@pytest.mark.parametrize("value", ["black,scale=1:1", "a:b", "red;x", "x'y", "", "#12", "0xGG0000"])
def test_pad_color_invalid_falls_back(value):
    assert validate_ffmpeg_color(value) == "black"


def test_pad_filter_uses_validated_color():
    r = generate_filters(selected_track=0, source=Path("in.mkv"), pad_aspect="16:9", pad_color="red,scale=1:1")
    assert "color=black" in r[1] and "scale=1:1" not in r[1]


def test_start_extra_keeps_windows_backslashes():
    with mock.patch("fastflix.encoders.common.helpers.sys.platform", "win32"):
        cmd = generate_ffmpeg_start(
            source=Path("a.mkv"),
            ffmpeg=Path("ffmpeg"),
            encoder="libx265",
            selected_track=0,
            start_extra=r"-hwaccel d3d11va -i C:\dir\file.png",
        )
    assert r"C:\dir\file.png" in cmd


def test_eq_has_no_eval_frame():
    r = generate_filters(selected_track=0, source=Path("in.mkv"), brightness="0.1")
    assert "eq=brightness=0.1" in r[1]
    assert "eval=frame" not in r[1]
