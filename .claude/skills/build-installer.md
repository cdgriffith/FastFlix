---
description: Build the FastFlix installer, distribution, launcher, and uninstaller
---

# Building the FastFlix Installer & Distribution

## Prerequisites

- Go 1.22+ installed
- `go-winres` installed (pinned): `go install github.com/tc-hib/go-winres@v0.3.3`, with `%GOPATH%\bin` on PATH
- Python 3.13+ with `uv`
- Internet access (first build downloads embeddable Python and wheels)

`zstandard` is not a project dependency; run the script through `uv run --with zstandard`.

## Full Build (everything from scratch)

```bash
uv run --with zstandard python scripts/build_distribution.py --archive --installer
```

This produces `dist/FastFlix_installer.exe`. The script:
- Downloads the embeddable Python (version constant `DEFAULT_PYTHON_VERSION` in the script)
- Builds a fresh FastFlix wheel (wipes `dist/wheels`, requires exactly one wheel)
- Installs dependencies pinned from `uv.lock` for the bundled CPython 3.13 / win_amd64 (`--arch arm64` for ARM64)
- Syncs `cmd/*/winres/winres.json` with `fastflix/version.py` (versions + copyright year)
- Runs `go-winres make` in each `cmd/*` and builds `FastFlix.exe` + `uninstall.exe` (+ installer with `--installer`)
  with `-X main.Version=... -X main.BuildDate=...`
- Trims unused PySide6 modules (~527 MB savings), keeping third-party licence files
- Creates `fastflix_dist.tar.zst`, copies `licenses.txt`, generates `terms_translations.json`

Use `--archive` alone to stop before building the installer.

## Manual rebuilds (after Go code changes)

Run `go-winres make` in the `cmd/<name>` directory first (the `.syso` files are gitignored), then:

```bash
go build -ldflags="-s -w -X main.Version=6.3.0 -X main.BuildDate=2026-01-01" -o dist/FastFlix/FastFlix.exe ./cmd/launcher
go build -ldflags="-s -w -H windowsgui -X main.Version=6.3.0" -o dist/FastFlix/uninstall.exe ./cmd/uninstaller
go build -ldflags="-s -w -H windowsgui -X main.Version=6.3.0 -X main.BuildDate=2026-01-01" -o dist/FastFlix_installer.exe ./cmd/installer   # needs the archive
```

## Checks

```bash
GOOS=windows go vet ./...
go test ./cmd/internal/...
```

## Important Notes

- **Launcher**: Built WITHOUT `-H windowsgui` (needs console for logs); passes all arguments through to `python -m fastflix`
- **Installer/Uninstaller**: Built WITH `-H windowsgui` (no console)
- **Shared logic** (path safety, manifest-based removal, registry, self-delete batch) is in `cmd/internal/ffinstall`; never delete directories with `RemoveAll` on a registry-derived path without `ffinstall.SafeToRemove`
- **Uninstall** removes only files listed by `install_manifest.txt` (top-level entries) and keeps user files like a portable `fastflix.yaml`
- **DO NOT** use `CREATE_NO_WINDOW` flag on the launcher's child process - breaks FFmpeg pipe handles
- **DO NOT** use `walk` or other Go GUI frameworks - they have `TTM_ADDTOOL` failures on modern Windows. Use raw Win32 API.
- For `WM_DRAWITEM`-style lParam casts use `*(**T)(unsafe.Pointer(&lParam))` (keeps `go vet` clean)

## Testing

```bash
dist/FastFlix/FastFlix.exe --version
dist/FastFlix/FastFlix.exe --test
dist/FastFlix_installer.exe
"%LOCALAPPDATA%\Programs\FastFlix\uninstall.exe"
```
