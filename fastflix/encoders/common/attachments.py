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


def build_attachments(attachments: list[AttachmentTrack]) -> List[str]:
    commands = []
    for attachment in attachments:
        if attachment.attachment_type == "cover":
            mime_type, ext_type = image_type(attachment.file_path)
            commands.extend(
                [
                    "-attach",
                    str(attachment.file_path),
                    f"-metadata:s:{attachment.outdex}",
                    f"mimetype={mime_type}",
                    f"-metadata:s:{attachment.outdex}",
                    f"filename={attachment.filename}.{ext_type}",
                ]
            )
    return commands
