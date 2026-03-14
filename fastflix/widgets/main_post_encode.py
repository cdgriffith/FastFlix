#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from fastflix.models.video import Video

if TYPE_CHECKING:
    from fastflix.widgets.main import Main

logger = logging.getLogger("fastflix")


class PostEncodeMixin:
    """Mixin for Main: post-encode validation, history recording, and file renaming."""

    self: Main

    def _post_encode_process(self, video: Video):
        """Run ffprobe validation and post-encode rename on completed video."""
        try:
            from fastflix.naming import has_post_encode_placeholders

            output_path = video.video_settings.output_path
            if not output_path or not output_path.exists():
                logger.warning(f"Post-encode: output file not found at {output_path}")
                return

            # Always run ffprobe for validation
            try:
                from fastflix.flix import probe

                probe_data = probe(self.app, output_path)
            except Exception:
                logger.exception(f"Post-encode: ffprobe failed on {output_path}")
                probe_data = None

            self._validate_output(output_path, probe_data)

            # Rename if post-encode placeholders exist in filename
            if has_post_encode_placeholders(output_path.stem):
                self._rename_with_post_encode_vars(video, probe_data)

            # Record to history if enabled
            if self.app.fastflix.config.enable_history:
                try:
                    self._record_history(video)
                except Exception:
                    logger.exception("Failed to record history entry")

        except Exception:
            logger.exception("Post-encode processing failed (encode itself succeeded)")

    def _record_history(self, video: Video, success: bool = True):
        """Record a completed or failed encoding to history."""
        import uuid as uuid_mod
        from datetime import datetime as dt

        from fastflix.models.history import (
            HistoryEntry,
            add_history_entry,
            build_settings_summary,
            get_history_thumbnails_dir,
        )

        output_path = video.video_settings.output_path
        encoder_settings = video.video_settings.video_encoder_settings

        # Build audio summary
        audio_parts = []
        for track in video.audio_tracks:
            if track.enabled:
                codec = track.conversion_codec if track.conversion_codec else track.codec
                audio_parts.append(f"{track.language} ({codec})")
        audio_summary = ", ".join(audio_parts) if audio_parts else ""

        # Build subtitle summary
        sub_parts = []
        for track in video.subtitle_tracks:
            if track.enabled:
                sub_parts.append(f"{track.language} ({track.subtitle_type})")
        subtitle_summary = ", ".join(sub_parts) if sub_parts else ""

        # Resolution
        resolution = ""
        if video.width and video.height:
            resolution = f"{video.width}x{video.height}"

        # File size
        file_size = 0
        try:
            if output_path and output_path.exists():
                file_size = output_path.stat().st_size
        except Exception:
            pass

        # Duration
        duration = 0.0
        if video.duration:
            duration = video.duration

        # Encode duration
        encode_duration_secs = 0.0
        if video.status.encode_started_at:
            encode_duration_secs = (
                dt.now(video.status.encode_started_at.tzinfo) - video.status.encode_started_at
            ).total_seconds()

        entry_uuid = str(uuid_mod.uuid4())
        thumbnail_filename = f"{entry_uuid}.jpg"

        entry = HistoryEntry(
            uuid=entry_uuid,
            source=str(video.source),
            output=str(output_path) if output_path else "",
            encoder_name=encoder_settings.name,
            encoder_settings=encoder_settings.model_dump(),
            encoder_settings_summary=build_settings_summary(encoder_settings.model_dump()),
            audio_summary=audio_summary,
            subtitle_summary=subtitle_summary,
            resolution=resolution,
            duration=duration,
            file_size=file_size,
            completed_at=dt.now().isoformat(),
            thumbnail_filename=thumbnail_filename,
            success=success,
            encode_duration_secs=encode_duration_secs,
        )

        # Generate thumbnail directly from source video
        thumbs_dir = get_history_thumbnails_dir(self.app.fastflix.data_path)
        thumbs_dir.mkdir(parents=True, exist_ok=True)
        thumb_output = thumbs_dir / thumbnail_filename
        try:
            from subprocess import PIPE, STDOUT
            from subprocess import run as subprocess_run

            from fastflix.flix import generate_thumbnail_command

            thumb_command = generate_thumbnail_command(
                config=self.app.fastflix.config,
                source=video.source,
                output=thumb_output,
                filters=["-vf", "scale='min(440\\,iw):-8'"],
                start_time=video.video_settings.start_time or 0,
                input_track=video.video_settings.selected_track,
            )
            result = subprocess_run(thumb_command, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            if result.returncode != 0 or not thumb_output.exists():
                logger.warning("Failed to generate thumbnail for history entry")
                entry.thumbnail_filename = ""
        except Exception:
            logger.warning("Failed to generate thumbnail for history entry")
            entry.thumbnail_filename = ""

        add_history_entry(self.app.fastflix.data_path, entry, max_items=self.app.fastflix.config.history_max_items)

    def _validate_output(self, output_path: Path, probe_data):
        """Quick sanity check on the output file."""
        if not output_path.exists():
            logger.warning(f"Output validation: file does not exist: {output_path}")
            return

        file_size = output_path.stat().st_size
        if file_size < 1024:
            logger.warning(f"Output validation: file is suspiciously small ({file_size} bytes): {output_path}")

        if not probe_data:
            logger.warning(f"Output validation: no probe data available for {output_path}")
            return

        # Check for video stream
        has_video = False
        if hasattr(probe_data, "streams"):
            for stream in probe_data.streams:
                if stream.get("codec_type") == "video":
                    has_video = True
                    break
        if not has_video:
            logger.warning(f"Output validation: no video stream found in {output_path}")

        # Check duration
        if hasattr(probe_data, "format") and probe_data.format:
            duration = probe_data.format.get("duration")
            if duration:
                try:
                    if float(duration) <= 0:
                        logger.warning(f"Output validation: duration is 0 or negative for {output_path}")
                except (ValueError, TypeError):
                    pass

    def _rename_with_post_encode_vars(self, video: Video, probe_data):
        """Resolve post-encode placeholders and rename the output file."""
        from fastflix.naming import resolve_post_encode_variables

        output_path = video.video_settings.output_path
        encode_end = datetime.datetime.now(datetime.timezone.utc)
        encode_start = video.status.encode_started_at

        old_stem = output_path.stem
        new_stem = resolve_post_encode_variables(
            old_stem,
            output_path,
            probe_data,
            encode_start=encode_start,
            encode_end=encode_end,
        )

        if new_stem == old_stem:
            return

        new_path = output_path.with_stem(new_stem)

        # Handle collision
        if new_path.exists():
            rand_suffix = secrets.token_hex(2)
            new_path = output_path.with_stem(f"{new_stem}-{rand_suffix}")

        try:
            output_path.rename(new_path)
            video.video_settings.output_path = new_path
            logger.info(f"Post-encode rename: {output_path.name} -> {new_path.name}")
        except OSError:
            logger.exception(f"Post-encode rename failed: {output_path} -> {new_path}")
