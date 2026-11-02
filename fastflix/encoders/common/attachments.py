# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List

from fastflix.models.encode import AttachmentTrack


def image_type(file: Path | str) -> tuple[str | None, str | None]:
    if not file:
        return None, None
    mime_type = "image/jpeg"
    ext_type = "jpg"
    if Path(file).suffix.lower() == ".png":
        mime_type = "image/png"
        ext_type = "png"
    return mime_type, ext_type


def build_attachments(attachments: list[AttachmentTrack], mapped_attachment_count: int = 0) -> List[str]:
    """
    FFmpeg creates -attach streams after all mapped streams, so address them by attachment-type index
    (after any attachment streams mapped from the source) rather than a stored absolute stream index.
    """
    commands = []
    attachment_index = mapped_attachment_count
    for attachment in attachments:
        if attachment.attachment_type == "cover":
            mime_type, ext_type = image_type(attachment.file_path)
            commands.extend(
                [
                    "-attach",
                    str(attachment.file_path),
                    f"-metadata:s:t:{attachment_index}",
                    f"mimetype={mime_type}",
                    f"-metadata:s:t:{attachment_index}",
                    f"filename={attachment.filename}.{ext_type}",
                ]
            )
            attachment_index += 1
    return commands
