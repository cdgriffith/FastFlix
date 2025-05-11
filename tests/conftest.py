# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Union
import pytest

from box import Box
from pydantic import BaseModel

from fastflix.models.config import Config
from fastflix.models.encode import EncoderSettings, AudioTrack, SubtitleTrack, AttachmentTrack
from fastflix.models.fastflix import FastFlix
from fastflix.models.video import Video, VideoSettings


def create_fastflix_instance(
    encoder_settings: EncoderSettings, video_settings: Optional[VideoSettings] = None, hdr10_metadata: bool = False
):
    """
    Create a FastFlix instance with the given settings.

    Args:
        encoder_settings: The encoder-specific settings
        video_settings: The video settings (optional)
        hdr10_metadata: Whether to include HDR10 metadata (default: False)

    Returns:
        A FastFlix instance configured with the provided settings
    """
    # Use default video settings if none provided
    if video_settings is None:
        video_settings = VideoSettings(
            remove_hdr=False,
            maxrate=None,
            bufsize=None,
        )

    # Create a mock Video object
    video = Video(
        source=Path("input.mkv"),
        duration=60,
        streams=Box(
            {
                "video": [
                    Box(
                        {
                            "index": 0,
                            "codec_name": "hevc",
                            "codec_type": "video",
                            "pix_fmt": "yuv420p10le",
                            "color_space": "bt2020nc",
                            "color_transfer": "smpte2084",
                            "color_primaries": "bt2020",
                            "chroma_location": "left",
                        }
                    )
                ]
            }
        ),
        format=Box({}),
        video_settings=video_settings,
        work_path=Path("work_path"),
    )

    # Set the video encoder settings
    video.video_settings.video_encoder_settings = encoder_settings

    # Add HDR10 metadata if requested
    if hdr10_metadata:
        video.hdr10_streams = [
            Box(
                {
                    "index": 0,
                    "master_display": Box(
                        {
                            "green": "(0.2650,0.6900)",
                            "blue": "(0.1500,0.0600)",
                            "red": "(0.6800,0.3200)",
                            "white": "(0.3127,0.3290)",
                            "luminance": "(1000.0,0.0001)",
                        }
                    ),
                    "cll": "1000,300",
                }
            )
        ]

    # Create a Config instance with minimal required parameters
    config = Config(
        version="4.0.0",
        ffmpeg=Path("ffmpeg"),
        ffprobe=Path("ffprobe"),
        work_path=Path("work_path"),
    )

    # Create a FastFlix instance
    fastflix = FastFlix(
        config=config,
        encoders={},
        audio_encoders=[],
        current_video=video,
    )

    return fastflix


@pytest.fixture
def sample_audio_tracks():
    """
    Fixture providing sample audio tracks for testing.

    Returns:
        A list of AudioTrack objects for testing
    """
    return [
        AudioTrack(
            index=1,
            outdex=0,
            codec="truehd",
            title="Surround 5.1",
            language="eng",
            channels=6,
            enabled=True,
            raw_info=Box(
                {
                    "channel_layout": "5.1(side)",
                    "channels": 6,
                    "codec_name": "truehd",
                    "tags": {"title": "Surround 5.1", "language": "eng"},
                    "disposition": {"default": 0},
                }
            ),
            dispositions={"default": False},
        ),
        AudioTrack(
            index=2,
            outdex=1,
            codec="ac3",
            title="Stereo",
            language="jpn",
            channels=2,
            enabled=True,
            raw_info=Box(
                {
                    "channel_layout": "stereo",
                    "channels": 2,
                    "codec_name": "ac3",
                    "tags": {"title": "Stereo", "language": "jpn"},
                    "disposition": {"default": 1},
                }
            ),
            dispositions={"default": True},
        ),
        AudioTrack(
            index=3,
            outdex=2,
            codec="aac",
            title="Commentary",
            language="eng",
            channels=2,
            enabled=False,
            raw_info=Box(
                {
                    "channel_layout": "stereo",
                    "channels": 2,
                    "codec_name": "aac",
                    "tags": {"title": "Commentary", "language": "eng"},
                    "disposition": {"default": 0},
                }
            ),
            dispositions={"default": False},
        ),
    ]


@pytest.fixture
def sample_attachment_tracks():
    """
    Fixture providing sample attachment tracks for testing.

    Returns:
        A list of AttachmentTrack objects for testing
    """
    return [
        AttachmentTrack(index=0, outdex=0, attachment_type="cover", file_path="cover.jpg", filename="cover"),
        AttachmentTrack(index=1, outdex=1, attachment_type="cover", file_path="thumbnail.png", filename="thumbnail"),
    ]


@pytest.fixture
def sample_subtitle_tracks():
    """
    Fixture providing sample subtitle tracks for testing.

    Returns:
        A list of SubtitleTrack objects for testing
    """
    return [
        SubtitleTrack(
            index=0,
            outdex=0,
            language="eng",
            subtitle_type="text",
            enabled=True,
            burn_in=False,
            long_name="English",
            dispositions={"default": True, "forced": False},
        ),
        SubtitleTrack(
            index=1,
            outdex=1,
            language="jpn",
            subtitle_type="text",
            enabled=True,
            burn_in=False,
            long_name="Japanese",
            dispositions={"default": False, "forced": False},
        ),
        SubtitleTrack(
            index=2,
            outdex=2,
            language="eng",
            subtitle_type="text",
            enabled=True,
            burn_in=True,
            long_name="English (Forced)",
            dispositions={"default": False, "forced": True},
        ),
    ]


@pytest.fixture
def fastflix_instance(sample_audio_tracks, sample_attachment_tracks, sample_subtitle_tracks):
    """
    Fixture providing a FastFlix instance with sample data for testing.

    Args:
        sample_audio_tracks: Sample audio tracks from fixture
        sample_subtitle_tracks: Sample subtitle tracks from fixture
        sample_attachment_tracks: Sample attachment tracks from fixture

    Returns:
        A FastFlix instance configured with sample data
    """
    # Create a mock Video object
    video = Video(
        source=Path("input.mkv"),
        duration=60,
        streams=Box(
            {
                "video": [
                    Box(
                        {
                            "index": 0,
                            "codec_name": "hevc",
                            "codec_type": "video",
                            "pix_fmt": "yuv420p10le",
                            "color_space": "bt2020nc",
                            "color_transfer": "smpte2084",
                            "color_primaries": "bt2020",
                            "chroma_location": "left",
                        }
                    )
                ],
                "audio": sample_audio_tracks,
                "subtitle": [
                    track.raw_info if hasattr(track, "raw_info") else Box({"index": track.index})
                    for track in sample_subtitle_tracks
                ],
            }
        ),
        format=Box({}),
        video_settings=VideoSettings(remove_hdr=False, maxrate=None, bufsize=None, output_path=Path("output.mkv")),
        work_path=Path("work_path"),
        audio_tracks=sample_audio_tracks,
        subtitle_tracks=sample_subtitle_tracks,
        attachment_tracks=sample_attachment_tracks,
    )

    # Create a Config instance with minimal required parameters
    config = Config(
        version="4.0.0",
        ffmpeg=Path("ffmpeg"),
        ffprobe=Path("ffprobe"),
        work_path=Path("work_path"),
    )

    # Create a FastFlix instance
    fastflix = FastFlix(
        config=config,
        encoders={},
        audio_encoders=[],
        current_video=video,
        ffmpeg_version="n5.0",
    )

    return fastflix
