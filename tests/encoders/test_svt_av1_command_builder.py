# -*- coding: utf-8 -*-
from unittest import mock

from fastflix.encoders.common.helpers import null
from fastflix.encoders.svt_av1.command_builder import build
from fastflix.models.encode import SVTAV1Settings
from fastflix.models.video import VideoSettings

from tests.conftest import create_fastflix_instance


def _build_with_settings(**kwargs):
    """Helper to build SVT-AV1 commands with custom settings."""
    defaults = dict(
        qp=24,
        qp_mode="crf",
        speed="7",
        tile_columns="0",
        tile_rows="0",
        scene_detection=False,
        single_pass=True,
        bitrate=None,
    )
    defaults.update(kwargs)
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(**defaults),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None),
    )
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_gen:
        mock_gen.return_value = (["ffmpeg", "-y", "-i", "input.mkv"], ["output.mkv"], ["-r", "24"])
        with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_color_details") as mock_color:
            mock_color.return_value = []
            result = build(fastflix)
    cmd = result[0].command
    params_idx = cmd.index("-svtav1-params")
    params_value = cmd[params_idx + 1]
    return cmd, params_value


def test_svt_av1_single_pass_qp():
    """Test the build function with single-pass QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="crf",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=True,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert isinstance(cmd, list), f"Expected command to be a list, got {type(cmd)}"

            # Check key elements are present in the command list
            assert "-strict" not in cmd
            assert "-preset" in cmd
            assert "7" in cmd
            assert "-crf" in cmd
            assert "24" in cmd
            assert "-svtav1-params" in cmd
            assert "output.mkv" in cmd

            # Verify svtav1-params contains the expected parameters
            params_idx = cmd.index("-svtav1-params")
            params_value = cmd[params_idx + 1]
            assert "tile-columns=0" in params_value
            assert "tile-rows=0" in params_value
            assert "scd=0" in params_value


def test_svt_av1_two_pass_qp():
    """Test the build function with two-pass QP settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="qp",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=False,
            bitrate=None,
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            # Mock the secrets.token_hex function to return a predictable result
            with mock.patch("fastflix.encoders.svt_av1.command_builder.secrets.token_hex") as mock_token_hex:
                mock_token_hex.return_value = "abcdef1234"

                result = build(fastflix)

                assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
                assert len(result) == 2, f"Expected 2 Command objects, got {len(result)}"

                cmd1 = result[0].command
                cmd2 = result[1].command
                assert isinstance(cmd1, list), f"Expected command to be a list, got {type(cmd1)}"
                assert isinstance(cmd2, list), f"Expected command to be a list, got {type(cmd2)}"

                # First pass should have pass 1, -an, null output
                assert "-pass" in cmd1
                assert "1" in cmd1[cmd1.index("-pass") + 1 :][:1]
                assert "-an" in cmd1
                assert "-f" in cmd1
                assert "matroska" in cmd1
                assert null in cmd1
                assert "-passlogfile" in cmd1

                # Second pass should have pass 2, real output
                assert "-pass" in cmd2
                assert "2" in cmd2[cmd2.index("-pass") + 1 :][:1]
                assert "output.mkv" in cmd2


def test_svt_av1_single_pass_bitrate():
    """Test the build function with single-pass bitrate settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=None,
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=False,
            single_pass=True,
            bitrate="5000k",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert isinstance(cmd, list), f"Expected command to be a list, got {type(cmd)}"

            # Check key elements
            assert "-b:v" in cmd
            assert "5000k" in cmd
            assert "output.mkv" in cmd


def test_svt_av1_with_hdr():
    """Test the build function with HDR settings."""
    fastflix = create_fastflix_instance(
        encoder_settings=SVTAV1Settings(
            qp=24,
            qp_mode="crf",
            speed="7",
            tile_columns="0",
            tile_rows="0",
            scene_detection=True,
            single_pass=True,
            bitrate=None,
            pix_fmt="yuv420p10le",
        ),
        video_settings=VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        ),
        hdr10_metadata=True,
    )

    # Mock the generate_all function to return a predictable result (lists)
    with mock.patch("fastflix.encoders.svt_av1.command_builder.generate_all") as mock_generate_all:
        mock_generate_all.return_value = (
            ["ffmpeg", "-y", "-i", "input.mkv"],
            ["output.mkv"],
            ["-r", "24"],
        )

        # Mock the generate_color_details function to return a predictable result (list)
        with mock.patch(
            "fastflix.encoders.svt_av1.command_builder.generate_color_details"
        ) as mock_generate_color_details:
            mock_generate_color_details.return_value = ["-color_primaries", "bt2020"]

            result = build(fastflix)

            assert isinstance(result, list), f"Expected a list of Command objects, got {type(result)}"
            assert len(result) == 1, f"Expected 1 Command object, got {len(result)}"

            cmd = result[0].command
            assert isinstance(cmd, list), f"Expected command to be a list, got {type(cmd)}"

            # Verify svtav1-params contains HDR-related parameters
            params_idx = cmd.index("-svtav1-params")
            params_value = cmd[params_idx + 1]
            assert "scd=1" in params_value
            assert "color-primaries=9" in params_value
            assert "transfer-characteristics=16" in params_value
            assert "matrix-coefficients=9" in params_value
            assert "mastering-display=" in params_value
            assert "content-light=" in params_value
            assert "enable-hdr=1" in params_value


def test_svt_av1_with_tune():
    """Test that tune parameter is included when non-default."""
    _, params = _build_with_settings(tune="0")
    assert "tune=0" in params


def test_svt_av1_with_film_grain():
    """Test that film-grain parameter is included when set."""
    _, params = _build_with_settings(film_grain=8)
    assert "film-grain=8" in params
    assert "film-grain-denoise" not in params


def test_svt_av1_with_film_grain_denoise():
    """Test that film-grain-denoise is included when both film_grain and denoise are set."""
    _, params = _build_with_settings(film_grain=8, film_grain_denoise=True)
    assert "film-grain=8" in params
    assert "film-grain-denoise=1" in params


def test_svt_av1_with_sharpness():
    """Test that sharpness parameter is included when non-default."""
    _, params = _build_with_settings(sharpness="3")
    assert "sharpness=3" in params


def test_svt_av1_with_fast_decode():
    """Test that fast-decode parameter is included when non-default."""
    _, params = _build_with_settings(fast_decode="2")
    assert "fast-decode=2" in params


def test_svt_av1_defaults_no_extra_params():
    """Test that default settings don't add tune/film-grain/sharpness/fast-decode."""
    _, params = _build_with_settings()
    assert "tune=" not in params
    assert "film-grain=" not in params
    assert "sharpness=" not in params
    assert "fast-decode=" not in params


def test_svt_av1_new_options_default_output_unchanged():
    _, params = _build_with_settings()
    for key in ("variance", "enable-tf", "qm", "startup-mg-size"):
        assert key not in params


def test_svt_av1_variance_boost_enabled_defaults():
    _, params = _build_with_settings(enable_variance_boost=True)
    parts = params.split(":")
    assert "enable-variance-boost=1" in parts
    assert not any(p.startswith("variance-boost-strength") or p.startswith("variance-octile") for p in parts)


def test_svt_av1_variance_boost_custom_values():
    _, params = _build_with_settings(enable_variance_boost=True, variance_boost_strength="3", variance_octile="7")
    parts = params.split(":")
    assert "enable-variance-boost=1" in parts
    assert "variance-boost-strength=3" in parts
    assert "variance-octile=7" in parts


def test_svt_av1_variance_values_ignored_when_disabled():
    _, params = _build_with_settings(variance_boost_strength="3", variance_octile="7")
    assert "variance" not in params


def test_svt_av1_tune_new_values():
    _, params = _build_with_settings(tune="3")
    assert "tune=3" in params.split(":")


def test_svt_av1_enable_tf_startup_mg_size():
    _, params = _build_with_settings(enable_tf="2", startup_mg_size="3")
    parts = params.split(":")
    assert "enable-tf=2" in parts
    assert "startup-mg-size=3" in parts


def test_svt_av1_quant_matrices():
    _, params = _build_with_settings(enable_qm=True, qm_min="2", qm_max="10")
    parts = params.split(":")
    assert "enable-qm=1" in parts
    assert "qm-min=2" in parts
    assert "qm-max=10" in parts
    _, params = _build_with_settings(enable_qm=True)
    assert params.split(":").count("enable-qm=1") == 1
    assert "qm-min" not in params


def test_svt_av1_user_params_merge_and_ui_wins():
    _, params = _build_with_settings(svtav1_params=["enable-tf=0", "foo=1"], enable_tf="2")
    parts = params.split(":")
    assert parts[:2] == ["enable-tf=0", "foo=1"]
    assert parts.index("enable-tf=2") > parts.index("enable-tf=0")


def test_svt_av1_film_grain_full_range():
    _, params = _build_with_settings(film_grain=50)
    assert "film-grain=50" in params.split(":")
