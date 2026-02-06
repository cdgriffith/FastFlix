# -*- coding: utf-8 -*-
import gc
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from queue import Queue, Empty
from typing import Optional

from box import Box, BoxError
from ruamel.yaml import YAMLError

from fastflix.models.video import Video, VideoSettings, Status, Crop
from fastflix.models.encode import AttachmentTrack
from fastflix.models.encode import setting_types
from fastflix.models.config import Config

logger = logging.getLogger("fastflix")

# Global lock for queue file operations within this process
_queue_file_lock = threading.Lock()

# Track the last known generation ID for each queue file
_generation_tracker: dict[str, str] = {}


@contextmanager
def queue_file_lock(queue_file: Path, timeout: float = 30.0):
    """
    Context manager that acquires both an in-process lock and a file-based lock.

    Uses a .lock file to prevent concurrent writes from multiple FastFlix instances.
    The lock file is automatically cleaned up when the context exits.

    Args:
        queue_file: Path to the queue file being protected
        timeout: Maximum time to wait for lock acquisition
    """
    lock_file = queue_file.with_suffix(".lock")
    start_time = time.time()
    lock_acquired = False

    # First acquire the in-process lock
    with _queue_file_lock:
        # Then try to acquire file-based lock
        while time.time() - start_time < timeout:
            try:
                # Try to create lock file exclusively
                # os.O_CREAT | os.O_EXCL fails if file exists
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                lock_acquired = True
                break
            except FileExistsError:
                # Lock file exists - check if it's stale (older than 60 seconds)
                try:
                    if lock_file.exists():
                        age = time.time() - lock_file.stat().st_mtime
                        if age > 60:
                            # Stale lock, remove it
                            logger.warning(f"Removing stale queue lock file (age: {age:.1f}s)")
                            lock_file.unlink(missing_ok=True)
                            continue
                except OSError:
                    pass
                time.sleep(0.1)
            except OSError as e:
                logger.warning(f"Error acquiring queue lock: {e}")
                time.sleep(0.1)

        if not lock_acquired:
            logger.error(f"Timeout waiting for queue lock after {timeout}s")
            # Proceed anyway but warn - don't block the user forever
            yield False
            return

        try:
            yield True
        finally:
            # Release the lock
            try:
                lock_file.unlink(missing_ok=True)
            except OSError:
                pass


class AsyncQueueSaver:
    """
    Background thread for saving queue to disk without blocking the GUI.

    Uses a dedicated thread to handle YAML serialization and file I/O,
    ensuring the GUI remains responsive even with large queues.
    """

    def __init__(self):
        self._queue = Queue()
        self._shutdown = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """Start the background saver thread."""
        if self._thread is None or not self._thread.is_alive():
            self._shutdown = False
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def _worker(self):
        """Background worker that processes save requests."""
        while not self._shutdown:
            try:
                request = self._queue.get(timeout=0.5)
            except Empty:
                continue

            if request is None:  # Shutdown signal
                break

            queue_data, queue_file, config, expected_generation = request
            try:
                save_queue(queue_data, queue_file, config, expected_generation=expected_generation)
            except Exception:
                logger.exception("Async queue save failed")

    def save(self, queue: list, queue_file: Path, config: Optional["Config"] = None):
        """
        Queue a save operation to be performed asynchronously.

        Args:
            queue: List of Video objects to save
            queue_file: Path to save the queue YAML file
            config: Optional Config object for work paths
        """
        # Capture the expected generation at the time of queueing
        # This allows us to detect if another save completed between queueing and execution
        expected_generation = get_current_generation(queue_file)

        # Make a deep copy of the queue data to avoid race conditions
        import copy

        try:
            queue_copy = copy.deepcopy(queue)
        except Exception:
            logger.warning("Could not deep copy queue for async save, falling back to sync save")
            save_queue(queue, queue_file, config, expected_generation=expected_generation)
            return

        self._queue.put((queue_copy, queue_file, config, expected_generation))

    def shutdown(self, timeout: float = 5.0):
        """
        Shutdown the background saver thread gracefully.

        Args:
            timeout: Maximum time to wait for pending saves to complete
        """
        self._shutdown = True
        self._queue.put(None)  # Signal worker to exit
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def wait_for_pending(self, timeout: float = 10.0):
        """
        Wait for all pending save operations to complete.

        Args:
            timeout: Maximum time to wait
        """
        # Shutdown and restart the thread to ensure all pending saves complete
        self._queue.put(None)  # Flush marker
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            # Restart the thread for future saves
            self._shutdown = False
            self.start()


# Global async saver instance
_async_saver: Optional[AsyncQueueSaver] = None


def get_async_saver() -> AsyncQueueSaver:
    """Get or create the global async queue saver instance."""
    global _async_saver
    if _async_saver is None:
        _async_saver = AsyncQueueSaver()
        _async_saver.start()
    return _async_saver


def save_queue_async(queue: list[Video], queue_file: Path, config: Optional[Config] = None):
    """
    Save the queue asynchronously in a background thread.

    This prevents GUI blocking during YAML serialization and file I/O.
    """
    saver = get_async_saver()
    saver.save(queue, queue_file, config)


def shutdown_async_saver(timeout: float = 5.0):
    """Shutdown the async saver, waiting for pending saves to complete."""
    global _async_saver
    if _async_saver is not None:
        _async_saver.shutdown(timeout)
        _async_saver = None


def get_queue_generation(queue_file: Path) -> Optional[str]:
    """
    Read the generation ID from a queue file without loading the full queue.

    Returns None if file doesn't exist or has no generation marker.
    """
    if not queue_file.exists():
        return None
    try:
        loaded = Box.from_yaml(filename=queue_file)
        return loaded.get("_generation")
    except (BoxError, YAMLError):
        return None


def get_current_generation(queue_file: Path) -> Optional[str]:
    """Get the last known generation for a queue file from the tracker."""
    return _generation_tracker.get(str(queue_file))


def set_current_generation(queue_file: Path, generation: str):
    """Update the tracked generation for a queue file."""
    _generation_tracker[str(queue_file)] = generation


def get_queue(queue_file: Path) -> list[Video]:
    if not queue_file.exists():
        return []

    try:
        loaded = Box.from_yaml(filename=queue_file)
    except (BoxError, YAMLError):
        logger.exception("Could not open queue")
        return []

    # Update generation tracker with the loaded file's generation
    if "_generation" in loaded:
        set_current_generation(queue_file, loaded["_generation"])

    queue = []
    for video in loaded["queue"]:
        video["source"] = Path(video["source"])
        video["work_path"] = Path(video["work_path"])
        video["video_settings"]["output_path"] = Path(video["video_settings"]["output_path"])
        encoder_settings = video["video_settings"]["video_encoder_settings"]
        ves = [x(**encoder_settings) for x in setting_types.values() if x().name == encoder_settings["name"]][0]
        # audio = [AudioTrack(**x) for x in video["audio_tracks"]]
        # subtitles = [SubtitleTrack(**x) for x in video["subtitle_tracks"]]
        attachments = []
        for x in video["attachment_tracks"]:
            try:
                attachment_path = x.pop("file_path")
            except KeyError:
                attachment_path = None
            attachment = AttachmentTrack(**x)
            attachment.file_path = str(attachment_path) if attachment_path else None
            attachments.append(attachment)
        status = Status(**video["status"])
        crop = None
        if video["video_settings"]["crop"]:
            crop = Crop(**video["video_settings"]["crop"])
        del video["video_settings"]["video_encoder_settings"]
        del video["status"]
        del video["video_settings"]["crop"]
        vs = VideoSettings(
            **video["video_settings"],
            crop=crop,
        )
        vs.video_encoder_settings = ves  # No idea why this has to be called after, otherwise reset to x265
        del video["video_settings"]
        queue.append(Video(**video, video_settings=vs, status=status))
    del loaded
    return queue


def save_queue(
    queue: list[Video],
    queue_file: Path,
    config: Optional[Config] = None,
    expected_generation: Optional[str] = None,
):
    """
    Save the queue to a YAML file with generation tracking.

    Args:
        queue: List of Video objects to save
        queue_file: Path to save the queue YAML file
        config: Optional Config object for work paths
        expected_generation: If provided, verifies the file hasn't changed unexpectedly
    """
    items = []
    queue_file = Path(queue_file)

    if config is not None:
        queue_covers = config.work_path / "covers"
        queue_covers.mkdir(parents=True, exist_ok=True)
        queue_data = config.work_path / "queue_extras"
        queue_data.mkdir(parents=True, exist_ok=True)
    else:
        queue_data = Path()
        queue_covers = Path()

    def update_conversion_command(vid, old_path: str, new_path: str):
        for command in vid["video_settings"]["conversion_commands"]:
            new_command = command["command"].replace(old_path, new_path)
            if new_command == command["command"]:
                logger.error(f'Could not replace "{old_path}" with "{new_path}" in {command["command"]}')
            command["command"] = new_command

    for video in queue:
        video = video.model_dump()
        video["source"] = os.fspath(video["source"])
        video["work_path"] = os.fspath(video["work_path"])
        video["video_settings"]["output_path"] = os.fspath(video["video_settings"]["output_path"])
        if config:
            if metadata := video["video_settings"]["video_encoder_settings"].get("hdr10plus_metadata"):
                new_metadata_file = queue_data / f"{uuid.uuid4().hex}_metadata.json"
                try:
                    shutil.copy(metadata, new_metadata_file)
                except OSError:
                    logger.exception("Could not save HDR10+ metadata file to queue recovery location, removing HDR10+")

                update_conversion_command(
                    video,
                    str(metadata),
                    str(new_metadata_file),
                )
                video["video_settings"]["video_encoder_settings"]["hdr10plus_metadata"] = str(new_metadata_file)
            for track in video["attachment_tracks"]:
                if track.get("file_path"):
                    if not Path(track["file_path"]).exists():
                        logger.exception("Could not save cover to queue recovery location, removing cover")
                        continue
                    new_file = queue_covers / f"{uuid.uuid4().hex}_{Path(track['file_path']).name}"
                    try:
                        shutil.copy(track["file_path"], new_file)
                    except OSError:
                        logger.exception("Could not save cover to queue recovery location, removing cover")
                        continue
                    update_conversion_command(video, str(track["file_path"]), str(new_file))
                    track["file_path"] = str(new_file)

        items.append(video)

    # Use file lock and atomic write to prevent corruption
    with queue_file_lock(queue_file) as lock_acquired:
        if not lock_acquired:
            logger.warning("Proceeding with queue save without lock - potential race condition")

        # Verify generation if expected_generation was provided
        if expected_generation is not None:
            current_file_generation = get_queue_generation(queue_file)
            if current_file_generation is not None and current_file_generation != expected_generation:
                logger.error(
                    f"Queue file generation mismatch! Expected '{expected_generation}', "
                    f"but file has '{current_file_generation}'. "
                    "Another save completed between queue and execution. "
                    "Skipping this save to avoid overwriting newer data."
                )
                return  # Abort save - a newer save already completed

        # Generate new generation ID for this save
        new_generation = uuid.uuid4().hex

        try:
            tmp = Box(queue=items, _generation=new_generation)

            # Atomic write: write to temp file in same directory, then rename
            # This ensures we never have a partially written queue file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".yaml.tmp",
                prefix="queue_",
                dir=queue_file.parent,
            )
            try:
                os.close(temp_fd)  # Close the fd, Box.to_yaml will open it
                tmp.to_yaml(filename=temp_path)
                del tmp

                # Atomic rename (on POSIX this is atomic, on Windows it replaces)
                # Use shutil.move for cross-platform compatibility
                shutil.move(temp_path, queue_file)

                # Update the generation tracker after successful save
                set_current_generation(queue_file, new_generation)
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except Exception as err:
            logger.warning(items)
            logger.exception(f"Could not save queue! {err.__class__.__name__}: {err}")
            raise err from None
    gc.collect(2)
