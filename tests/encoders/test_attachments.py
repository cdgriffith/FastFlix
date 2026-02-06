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
    assert result == []


def test_build_attachments_with_cover(sample_attachment_tracks):
    """Test the build_attachments function with cover attachments."""
    result = build_attachments(sample_attachment_tracks)

    # Check that the result is a list
    assert isinstance(result, list)

    # Check that each attachment is included in the command list
    # First cover attachment: cover.jpg at outdex 0
    assert "-attach" in result
    assert "cover.jpg" in result
    assert "mimetype=image/jpeg" in result
    assert "filename=cover.jpg" in result

    # Second cover attachment: thumbnail.png at outdex 1
    assert "thumbnail.png" in result
    assert "mimetype=image/png" in result
    assert "filename=thumbnail.png" in result

    # Verify the structure by checking index-based ordering for first attachment
    first_attach_idx = result.index("-attach")
    assert result[first_attach_idx + 1] == "cover.jpg"
    assert result[first_attach_idx + 2] == "-metadata:s:0"
    assert result[first_attach_idx + 3] == "mimetype=image/jpeg"
    assert result[first_attach_idx + 4] == "-metadata:s:0"
    assert result[first_attach_idx + 5] == "filename=cover.jpg"

    # Verify the structure for second attachment
    second_attach_idx = result.index("-attach", first_attach_idx + 1)
    assert result[second_attach_idx + 1] == "thumbnail.png"
    assert result[second_attach_idx + 2] == "-metadata:s:1"
    assert result[second_attach_idx + 3] == "mimetype=image/png"
    assert result[second_attach_idx + 4] == "-metadata:s:1"
    assert result[second_attach_idx + 5] == "filename=thumbnail.png"


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

    # Check that the result is a list
    assert isinstance(result, list)

    # Verify first attachment with custom path and filename
    first_attach_idx = result.index("-attach")
    assert result[first_attach_idx + 1] == "path/to/cover.jpg"
    assert result[first_attach_idx + 2] == "-metadata:s:0"
    assert result[first_attach_idx + 3] == "mimetype=image/jpeg"
    assert result[first_attach_idx + 4] == "-metadata:s:0"
    assert result[first_attach_idx + 5] == "filename=movie_cover.jpg"

    # Verify second attachment with spaces in path and custom filename
    second_attach_idx = result.index("-attach", first_attach_idx + 1)
    assert result[second_attach_idx + 1] == "path/with spaces/thumbnail.png"
    assert result[second_attach_idx + 2] == "-metadata:s:1"
    assert result[second_attach_idx + 3] == "mimetype=image/png"
    assert result[second_attach_idx + 4] == "-metadata:s:1"
    assert result[second_attach_idx + 5] == "filename=movie_thumbnail.png"


def test_build_attachments_non_cover_type():
    """Test the build_attachments function with non-cover attachment types."""
    # Create attachment tracks with non-cover types
    attachments = [
        AttachmentTrack(index=0, outdex=0, attachment_type="cover", file_path="cover.jpg", filename="cover"),
        AttachmentTrack(
            index=1,
            outdex=1,
            attachment_type="font",
            file_path="font.ttf",
            filename="font",  # Non-cover type
        ),
    ]

    result = build_attachments(attachments)

    # Check that only the cover attachment is included in the command list
    assert "-attach" in result
    assert "cover.jpg" in result
    assert "mimetype=image/jpeg" in result
    assert "filename=cover.jpg" in result
    assert "font.ttf" not in result

    # Verify there is exactly one -attach entry (only the cover, not the font)
    assert result.count("-attach") == 1

    # Verify the structure of the single cover attachment
    attach_idx = result.index("-attach")
    assert result[attach_idx + 1] == "cover.jpg"
    assert result[attach_idx + 2] == "-metadata:s:0"
    assert result[attach_idx + 3] == "mimetype=image/jpeg"
    assert result[attach_idx + 4] == "-metadata:s:0"
    assert result[attach_idx + 5] == "filename=cover.jpg"
