# -*- coding: utf-8 -*-
from pathlib import Path

from fastflix.encoders.common.attachments import image_type, build_attachments
from fastflix.models.encode import AttachmentTrack


def test_image_type_jpg():
    """Test the image_type function with a JPEG file."""
    # Test with a .jpg file
    result_mime, result_ext = image_type(Path("cover.jpg"))
    assert result_mime == "image/jpeg"
    assert result_ext == "jpg"

    # Test with a .jpeg file
    result_mime, result_ext = image_type(Path("cover.jpeg"))
    assert result_mime == "image/jpeg"
    assert result_ext == "jpg"

    # Test with uppercase extension
    result_mime, result_ext = image_type(Path("COVER.JPG"))
    assert result_mime == "image/jpeg"
    assert result_ext == "jpg"


def test_image_type_png():
    """Test the image_type function with a PNG file."""
    # Test with a .png file
    result_mime, result_ext = image_type(Path("cover.png"))
    assert result_mime == "image/png"
    assert result_ext == "png"

    # Test with uppercase extension
    result_mime, result_ext = image_type(Path("COVER.PNG"))
    assert result_mime == "image/png"
    assert result_ext == "png"


def test_image_type_other():
    """Test the image_type function with other file types."""
    # Test with a non-image file (should default to JPEG)
    result_mime, result_ext = image_type(Path("document.txt"))
    assert result_mime == "image/jpeg"
    assert result_ext == "jpg"


def test_build_attachments_empty():
    """Test the build_attachments function with an empty list."""
    result = build_attachments([])
    assert result == ""


def test_build_attachments_with_cover(sample_attachment_tracks):
    """Test the build_attachments function with cover attachments."""
    result = build_attachments(sample_attachment_tracks)

    # Check that each attachment is included in the command
    assert '-attach "cover.jpg" -metadata:s:0 mimetype="image/jpeg" -metadata:s:0  filename="cover.jpg"' in result
    assert (
        '-attach "thumbnail.png" -metadata:s:1 mimetype="image/png" -metadata:s:1  filename="thumbnail.png"' in result
    )


def test_build_attachments_with_custom_paths():
    """Test the build_attachments function with custom file paths."""
    # Create attachment tracks with custom paths
    attachments = [
        AttachmentTrack(
            index=0, outdex=0, attachment_type="cover", file_path="path/to/cover.jpg", filename="movie_cover"
        ),
        AttachmentTrack(
            index=1,
            outdex=1,
            attachment_type="cover",
            file_path="path/with spaces/thumbnail.png",
            filename="movie_thumbnail",
        ),
    ]

    result = build_attachments(attachments)

    # Check that each attachment is included in the command with correct paths and filenames
    assert (
        '-attach "path/to/cover.jpg" -metadata:s:0 mimetype="image/jpeg" -metadata:s:0  filename="movie_cover.jpg"'
        in result
    )
    assert (
        '-attach "path/with spaces/thumbnail.png" -metadata:s:1 mimetype="image/png" -metadata:s:1  filename="movie_thumbnail.png"'
        in result
    )


def test_build_attachments_non_cover_type():
    """Test the build_attachments function with non-cover attachment types."""
    # Create attachment tracks with non-cover types
    attachments = [
        AttachmentTrack(index=0, outdex=0, attachment_type="cover", file_path="cover.jpg", filename="cover"),
        AttachmentTrack(
            index=1, outdex=1, attachment_type="font", file_path="font.ttf", filename="font"  # Non-cover type
        ),
    ]

    result = build_attachments(attachments)

    # Check that only the cover attachment is included in the command
    assert '-attach "cover.jpg" -metadata:s:0 mimetype="image/jpeg" -metadata:s:0  filename="cover.jpg"' in result
    assert "font.ttf" not in result
