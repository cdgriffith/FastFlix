# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastFlix is a Python GUI application for video encoding/transcoding using PySide6 (Qt6). It wraps FFmpeg and supports 25+ encoder backends including x264, x265, AV1 variants, VP9, VVC, and hardware encoders (NVIDIA NVEncC, Intel QSVEncC, AMD VCEEncC).

**Requirements:** Python 3.13+, FFmpeg 4.3+ (5.0+ recommended)

## Build & Development Commands

```bash
# Install dependencies
uv sync --frozen

# Lint and format
uv run ruff check              # Check for violations
uv run ruff check --fix        # Auto-fix issues
uv run ruff format             # Format code

# Run tests
uv run pytest tests -v
PYTEST_QT_API=pyside6 uv run pytest tests -v  # Linux with Qt

# Run specific test file
uv run pytest tests/encoders/test_hevc_x265_command_builder.py -v

# Run the application
python -m fastflix

# Build executables
uv run pyinstaller FastFlix_Windows_OneFile.spec
uv run pyinstaller FastFlix_Nix_OneFile.spec
```

## Code Style

- Line length: 120 characters
- Double quotes for strings
- Ruff for linting and formatting (Black-compatible)
- Type hints via Pydantic models

## Architecture

### Multi-Process Design
- **Main process** (`entry.py`): Sets up queues and spawns worker subprocess
- **GUI process** (`application.py`): Qt application (prevents UI blocking)
- **Worker process** (`conversion_worker.py`): Processes conversion queue
- Queue communication between processes for status/logging

### Encoder Plugin System
Each encoder lives in `fastflix/encoders/{encoder_name}/` with:
- `__init__.py`: Encoder metadata/registration
- `command_builder.py`: Implements `build(fastflix) -> List[Command]`
- Settings model in `models/encode.py` (Pydantic)
- UI panel in `widgets/panels/{encoder_name}/`

### Key Modules
| Module | Purpose |
|--------|---------|
| `flix.py` | Core FFmpeg/FFprobe interaction |
| `widgets/main.py` | Main GUI window |
| `models/config.py` | Configuration management |
| `models/encode.py` | Encoder settings models |
| `encoders/common/helpers.py` | Shared command building utilities |

### Data Flow
1. User loads video → `parse()` via FFprobe
2. Encoding options set → Pydantic model validation
3. Video queued → Added to `conversion_list`
4. Worker processes → Encoder's `build()` generates FFmpeg commands
5. `command_runner.py` executes → Progress streamed to GUI

## Adding a New Encoder

1. Create directory: `fastflix/encoders/{encoder_name}/`
2. Add settings class to `models/encode.py`
3. Implement `command_builder.py` with `build(fastflix) -> List[Command]`
4. Create UI panel in `widgets/panels/{encoder_name}/`
5. Add tests in `tests/encoders/test_{encoder_name}_command_builder.py`

## Configuration

- Config file: `~/.config/FastFlix/fastflix.yaml`
- Portable mode: Place `fastflix.yaml` in app directory
- Environment overrides: `FF_FFMPEG`, `FF_FFPROBE`, `FF_HDR10PLUS`, `FF_CONFIG`

## FFmpeg Command Research

**IMPORTANT:** Always research FFmpeg commands online before implementing or modifying encoder command builders. FFmpeg options and filter syntax can change between versions.

Resources to consult:
- Official FFmpeg documentation: https://ffmpeg.org/ffmpeg.html
- FFmpeg filters documentation: https://ffmpeg.org/ffmpeg-filters.html
- FFmpeg wiki: https://trac.ffmpeg.org/wiki

Key considerations:
- Filter order matters (e.g., scale before palettegen for GIFs)
- Use appropriate scale flags (lanczos/bicubic over bilinear)
- Verify filter_complex syntax for multi-input/output chains
- Check encoder-specific options in official docs

## Changelog

**IMPORTANT:** Always update the `CHANGES` file when making significant additions or bug fixes during a session. Add entries under the current version section at the top of the file using the format:
- `* Adding {feature description}` for new features
- `* Fixing {bug description}` for bug fixes

## Branching

- `master`: Release branch
- `develop`: Development branch (PRs merge here)
