# -*- coding: utf-8 -*-
from pathlib import Path

from fastflix.encoders.gif.command_builder import build
from fastflix.models.encode import GIFSettings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build(remove_hdr=False, video_speed=1, scale_fps="15", tone_map="hable", **vs):
    fastflix = create_fastflix_instance(
        encoder_settings=GIFSettings(fps=scale_fps),
        video_settings=VideoSettings(
            remove_hdr=remove_hdr,
            tone_map=tone_map,
            video_speed=video_speed,
            maxrate=None,
            bufsize=None,
            output_path=Path("output.gif"),
            **vs,
        ),
    )
    fastflix.config.ffmpeg = Path("ffmpeg")
    return build(fastflix)


def _graph(cmd):
    return cmd[cmd.index("-filter_complex") + 1]


def test_gif_two_commands():
    result = _build()
    assert [c.name for c in result] == ["Palette generation", "GIF creation"]


def test_gif_fps_is_first_filter_before_scale():
    result = _build(scale_fps="10")
    for res in result:
        graph = _graph(res.command)
        assert "[0:0]fps=10" in graph, graph


def test_gif_fps_before_scale_when_scaling():
    result = _build(resolution_method="width", resolution_custom="320")
    for res in result:
        graph = _graph(res.command)
        assert "scale=" in graph
        assert graph.index("fps=") < graph.index("scale="), graph


def test_gif_palettegen_follows_same_chain_as_paletteuse_input():
    result = _build()
    pal_graph = _graph(result[0].command)
    gif_graph = _graph(result[1].command)
    base = gif_graph.split(";")[0]
    assert pal_graph.startswith(base + ";")
    assert "palettegen=stats_mode=full" in pal_graph
    assert "paletteuse=dither=sierra2_4a" in gif_graph


def test_gif_hdr_tone_map_applied_when_remove_hdr():
    result = _build(remove_hdr=True, tone_map="mobius")
    for res in result:
        graph = _graph(res.command)
        assert "tonemap=tonemap=mobius" in graph


def test_gif_no_tone_map_without_remove_hdr():
    for res in _build(remove_hdr=False):
        assert "tonemap" not in _graph(res.command)


def test_gif_fps_stays_last_when_speed_changed():
    result = _build(video_speed=2, scale_fps="10")
    graph = _graph(result[1].command).split(";")[0]
    assert graph.index("setpts=2*PTS") < graph.index("fps=10")
