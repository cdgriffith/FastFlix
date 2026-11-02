#!/usr/bin/env python3
"""
Build script for FastFlix distribution using embeddable Python.

Replaces PyInstaller by bundling the official Python embeddable distribution
with the pinned dependencies. The output is a self-contained directory
that can be launched via the Go launcher.

Usage:
    python scripts/build_distribution.py [--python-version 3.13.16] [--arch amd64] [--output dist/FastFlix]
        [--archive] [--installer]

Requirements:
    - Go and go-winres (go install github.com/tc-hib/go-winres@v0.3.3) on PATH
    - uv on PATH (dependencies are pinned from uv.lock via `uv export`)
    - Internet access (downloads Python embeddable distribution and wheels)
    - Or: pre-downloaded embeddable Python in scripts/cache/
"""

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "scripts" / "cache"

# Single source of truth for the bundled interpreter. Must be a 3.13.x patch release that
# has python-<ver>-embed-<arch>.zip published on python.org. Wheels are resolved for its minor version.
DEFAULT_PYTHON_VERSION = "3.13.16"

# Go commands that get built (directories under cmd/)
GO_CMDS = ("installer", "launcher", "uninstaller")

# Packages whose "tests" directory is known to be safe to delete (never imported at runtime).
SAFE_TEST_DIR_PACKAGES = ("numpy", "cv2", "psutil", "pydantic", "pydantic_core", "requests", "chardet")


def detect_arch():
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64", "x64"):
        return "amd64"
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "amd64"


def download_file(url, dest):
    """Download a file with progress indication."""
    print(f"  Downloading {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    print(f"  Saved to {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def get_python_url(version, arch):
    """Get the download URL for the Python embeddable distribution."""
    return f"https://www.python.org/ftp/python/{version}/python-{version}-embed-{arch}.zip"


def extract_python(python_zip, target_dir):
    """Extract the embeddable Python distribution."""
    print(f"  Extracting Python to {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(python_zip) as zf:
        zf.extractall(target_dir)


def configure_pth_file(python_dir):
    """Configure the ._pth file to enable site packages and find our lib directory.

    The embeddable distribution uses a ._pth file to restrict imports.
    We need to:
    1. Uncomment 'import site' to enable pip/site-packages
    2. Add '../lib' so Python can find our installed packages
    """
    pth_files = list(python_dir.glob("python*._pth"))
    if not pth_files:
        print("  WARNING: No ._pth file found in Python distribution")
        return

    pth_file = pth_files[0]
    print(f"  Configuring {pth_file.name}")

    lines = pth_file.read_text().splitlines()
    new_lines = []
    for line in lines:
        # Uncomment 'import site'
        if line.strip() == "#import site":
            new_lines.append("import site")
        else:
            new_lines.append(line)

    # Add our lib directory
    new_lines.append("../lib")

    pth_file.write_text("\n".join(new_lines) + "\n")


def get_version():
    """Return fastflix.version.__version__ (parsed from the file so there are no import side effects)."""
    text = (PROJECT_ROOT / "fastflix" / "version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        print("  ERROR: could not read __version__ from fastflix/version.py")
        sys.exit(1)
    return match.group(1)


def four_part_version(version):
    """Convert a PEP 440 version (6.3.0, 6.3.0b1) to the X.X.X.X form used by Windows resources."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)(\d+))?", version)
    if not match:
        return f"{version}.0"
    major, minor, patch, pre = match.groups()
    return f"{major}.{minor}.{patch}.{pre or 0}"


def require_tool(name, hint):
    if shutil.which(name) is None:
        print(f"  ERROR: '{name}' not found on PATH. {hint}")
        sys.exit(1)


def patch_winres(version):
    """Sync version numbers and copyright year in every cmd/*/winres/winres.json with fastflix/version.py."""
    four = four_part_version(version)
    year = datetime.now().year
    for cmd in GO_CMDS:
        path = PROJECT_ROOT / "cmd" / cmd / "winres" / "winres.json"
        old_text = path.read_text(encoding="utf-8")
        data = json.loads(old_text)
        data["RT_MANIFEST"]["#1"]["0409"]["identity"]["version"] = four
        ver = data["RT_VERSION"]["#1"]["0000"]
        ver["fixed"]["file_version"] = four
        ver["fixed"]["product_version"] = four
        info = ver["info"]["0409"]
        info["FileVersion"] = version
        info["ProductVersion"] = version
        info["LegalCopyright"] = re.sub(r"2019-\d{4}", f"2019-{year}", info["LegalCopyright"])
        new_text = json.dumps(data, indent=2) + "\n"
        if new_text != old_text:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            print(f"  Updated {path.relative_to(PROJECT_ROOT)} -> {version}")


def run_winres(cmd):
    """Generate the .syso resource (icon, manifest, version info) for cmd/<cmd>."""
    subprocess.run(["go-winres", "make"], check=True, cwd=PROJECT_ROOT / "cmd" / cmd)


def go_build(cmd, output, version, gui):
    """Build cmd/<cmd> with version and build date injected."""
    ldflags = f"-s -w -X main.Version={version} -X main.BuildDate={datetime.now().strftime('%Y-%m-%d')}"
    if gui:
        ldflags += " -H windowsgui"
    subprocess.run(
        ["go", "build", f"-ldflags={ldflags}", "-o", str(output), f"./cmd/{cmd}"],
        check=True,
        cwd=PROJECT_ROOT,
    )
    print(f"  Built {output.name} ({output.stat().st_size / 1024 / 1024:.1f} MB)")


def build_wheel(project_root):
    """Build a wheel of FastFlix with `uv build` (the uv-managed venv has no pip).

    The wheel directory is wiped first so a stale wheel can never be bundled.
    """
    wheel_dir = project_root / "dist" / "wheels"
    if wheel_dir.exists():
        shutil.rmtree(wheel_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)

    print("  Building FastFlix wheel...")
    require_tool("uv", "Install uv: https://docs.astral.sh/uv/")
    subprocess.run(["uv", "build", "--wheel", "--out-dir", str(wheel_dir), str(project_root)], check=True)

    wheels = list(wheel_dir.glob("fastflix-*.whl"))
    if len(wheels) != 1:
        print(f"  ERROR: expected exactly one fastflix wheel in {wheel_dir}, found {len(wheels)}: {wheels}")
        sys.exit(1)
    print(f"  Built {wheels[0].name} (fastflix/version.py says {get_version()})")
    return wheels[0]


def export_requirements(project_root, dest):
    """Write the exact dependency pins from uv.lock (runtime deps only, not the project itself)."""
    require_tool("uv", "Install uv: https://docs.astral.sh/uv/")
    result = subprocess.run(
        ["uv", "export", "--frozen", "--no-dev", "--no-hashes", "--no-emit-project", "--format", "requirements.txt"],
        check=True,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(result.stdout, encoding="utf-8")
    return dest


def install_dependencies(lib_dir, project_root, python_version, arch):
    """Install FastFlix and all dependencies into the lib directory.

    Uses `uv pip install --target` with an explicit target platform/interpreter, so wheels are resolved for the
    *bundled* CPython 3.13 (win_amd64/win_arm64) rather than for whatever Python runs this script. (Plain
    `pip --platform` cannot be used because a few pure-Python dependencies are sdist-only.) Dependency versions
    are pinned to uv.lock via `uv export`.
    """
    lib_dir.mkdir(parents=True, exist_ok=True)

    wheel_path = build_wheel(project_root)
    requirements = export_requirements(project_root, project_root / "dist" / "requirements-build.txt")

    py_minor = ".".join(python_version.split(".")[:2])
    uv_platform = "aarch64-pc-windows-msvc" if arch == "arm64" else "x86_64-pc-windows-msvc"
    target_args = [
        "--target",
        str(lib_dir),
        "--python-version",
        py_minor,
        "--python-platform",
        uv_platform,
        "--no-deps",  # the requirements file is fully resolved and pinned by uv
    ]

    print(f"  Installing pinned dependencies for CPython {py_minor} / {uv_platform}...")
    subprocess.run(["uv", "pip", "install", "-r", str(requirements), *target_args], check=True, cwd=project_root)

    print("  Installing FastFlix wheel...")
    subprocess.run(["uv", "pip", "install", str(wheel_path), *target_args], check=True, cwd=project_root)


def prepare_installer_resources():
    """Copy files needed by the Go installer for embedding (licenses, terms, etc.)."""
    installer_dir = PROJECT_ROOT / "cmd" / "installer"

    # Copy licenses for go:embed
    licenses_src = PROJECT_ROOT / "docs" / "build-licenses.txt"
    licenses_dst = installer_dir / "licenses.txt"
    if licenses_src.exists():
        shutil.copy2(licenses_src, licenses_dst)
        print(f"  Copied {licenses_src.name} -> {licenses_dst}")

    # Generate translated terms JSON for installer embedding
    generate_terms_json(installer_dir)


def generate_terms_json(installer_dir):
    """Generate translated terms text for all supported languages.

    Reads TERMS_SECTIONS from terms_agreement.py and translations from languages.yaml,
    then writes a JSON file mapping language codes to rendered terms text.
    """
    import json

    import yaml

    from fastflix.widgets.terms_agreement import TERMS_SECTIONS

    lang_file = PROJECT_ROOT / "fastflix" / "data" / "languages.yaml"
    with open(lang_file, encoding="utf-8") as f:
        lang_data = yaml.safe_load(f)

    languages = ["eng", "deu", "fra", "ita", "spa", "chs", "jpn", "rus", "por", "swe", "pol", "ukr", "kor", "ron"]

    result = {}
    for lang in languages:
        parts = []
        for header, body in TERMS_SECTIONS:
            translated_header = lang_data.get(header, {}).get(lang, header)
            if body:
                translated_body = lang_data.get(body, {}).get(lang, body)
                parts.append(f"{translated_header}\r\n{translated_body}")
            else:
                parts.append(translated_header)
        result[lang] = "\r\n\r\n".join(parts)

    out = installer_dir / "terms_translations.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Generated terms_translations.json ({len(languages)} languages)")


def build_go_launcher(output_dir):
    """Build the Go launcher and uninstaller and place them in the distribution."""
    version = get_version()
    require_tool("go", "Install Go: https://go.dev/dl/")
    require_tool("go-winres", "Install it: go install github.com/tc-hib/go-winres@v0.3.3")

    patch_winres(version)
    for cmd in ("launcher", "uninstaller"):
        run_winres(cmd)

    print(f"  Building launcher -> {output_dir / 'FastFlix.exe'}")
    go_build("launcher", output_dir / "FastFlix.exe", version, gui=False)

    print(f"  Building uninstaller -> {output_dir / 'uninstall.exe'}")
    go_build("uninstaller", output_dir / "uninstall.exe", version, gui=True)


def build_go_installer(output_exe):
    """Build the installer. Requires cmd/installer/fastflix_dist.tar.zst (see --archive)."""
    version = get_version()
    require_tool("go", "Install Go: https://go.dev/dl/")
    require_tool("go-winres", "Install it: go install github.com/tc-hib/go-winres@v0.3.3")
    patch_winres(version)
    run_winres("installer")
    output_exe.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Building installer -> {output_exe}")
    go_build("installer", output_exe, version, gui=True)


def copy_data_files(output_dir, project_root):
    """Copy additional data files that aren't part of the Python package."""
    print("  Copying additional data files...")

    # CHANGES file
    changes = project_root / "CHANGES"
    if changes.exists():
        shutil.copy2(changes, output_dir / "CHANGES")

    # Build licenses
    licenses = project_root / "docs" / "build-licenses.txt"
    if licenses.exists():
        shutil.copy2(licenses, output_dir / "build-licenses.txt")

    # Create build version file
    version_file = output_dir / "build_version"
    branch = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except FileNotFoundError:
        pass

    timestamp = datetime.now().strftime("%Y.%m.%d-%H.%M")
    version_file.write_text(f"{get_version()}-{branch}-{timestamp}")


def create_dist_archive(output_dir, archive_path):
    """Create a tar.zst archive of the distribution for the installer to embed.

    Uses Zstandard compression for better ratio than ZIP Deflate (~20-25% smaller)
    while maintaining fast decompression during installation.
    """
    import tarfile

    try:
        import zstandard
    except ImportError:
        print("  ERROR: zstandard package not installed. Run this script via: uv run --with zstandard python ...")
        sys.exit(1)

    print(f"  Creating distribution archive: {archive_path}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Create tar in memory, then compress with zstd
    tar_path = archive_path.with_suffix(".tar")
    with tarfile.open(tar_path, "w") as tf:
        for file in output_dir.rglob("*"):
            if file.is_file():
                arcname = str(file.relative_to(output_dir))
                tf.add(file, arcname=arcname)

    # Compress with zstandard at level 22 (high compression, still fast decompress)
    cctx = zstandard.ZstdCompressor(level=22, threads=-1)
    with open(tar_path, "rb") as f_in, open(archive_path, "wb") as f_out:
        cctx.copy_stream(f_in, f_out)

    tar_path.unlink()  # Remove intermediate tar

    print(f"  Archive size: {archive_path.stat().st_size / 1024 / 1024:.1f} MB")


def trim_pyside6(lib_dir):
    """Remove unused PySide6 modules to dramatically reduce distribution size.

    FastFlix only uses QtCore, QtGui, QtWidgets (and QtSvg for icon rendering).
    Uses a BLACKLIST approach: remove known-unnecessary large modules while
    keeping all runtime DLL dependencies intact (pyside6.abi3.dll, VC runtime, etc.).
    """
    print("  Trimming unused PySide6 modules...")
    pyside6_dir = lib_dir / "PySide6"
    if not pyside6_dir.exists():
        print("  WARNING: PySide6 directory not found")
        return 0

    removed_size = 0

    # Large DLL modules to REMOVE (prefixes matched case-insensitively)
    # These are Qt modules FastFlix does not use
    remove_dll_prefixes = (
        "Qt6WebEngine",  # Chromium browser engine (~193 MB)
        "Qt6Quick",  # QML/Quick UI framework (~35 MB)
        "Qt6Qml",  # QML engine (~12 MB)
        "Qt6Designer",  # Qt Designer (~7 MB)
        "Qt63D",  # 3D rendering (~8 MB)
        "Qt6Pdf",  # PDF rendering (~6 MB)
        "Qt6Multimedia",  # Multimedia playback (~2 MB)
        "Qt6ShaderTools",  # Shader compilation
        "Qt6Bluetooth",
        "Qt6Charts",
        "Qt6DataVisualization",
        "Qt6Graphs",
        "Qt6HttpServer",
        "Qt6Location",
        "Qt6Nfc",
        "Qt6Positioning",
        "Qt6RemoteObjects",
        "Qt6Scxml",
        "Qt6Sensors",
        "Qt6SerialBus",
        "Qt6SerialPort",
        "Qt6SpatialAudio",
        "Qt6StateMachine",
        "Qt6TextToSpeech",
        "Qt6WebChannel",
        "Qt6WebSockets",
        "Qt6WebView",
    )

    # .pyd Python bindings to REMOVE
    remove_pyd_prefixes = (
        "Qt3D",
        "QtAxContainer",
        "QtBluetooth",
        "QtCharts",
        "QtDataVisualization",
        "QtDBus",
        "QtDesigner",
        "QtGraphs",
        "QtHelp",
        "QtHttpServer",
        "QtLocation",
        "QtMultimedia",
        "QtNfc",
        "QtOpenGL",
        "QtPdf",
        "QtPositioning",
        "QtQml",
        "QtQuick",
        "QtRemoteObjects",
        "QtScxml",
        "QtSensors",
        "QtSerialBus",
        "QtSerialPort",
        "QtSpatialAudio",
        "QtSql",
        "QtStateMachine",
        "QtTest",
        "QtTextToSpeech",
        "QtUiTools",
        "QtWebChannel",
        "QtWebEngine",
        "QtWebSockets",
        "QtWebView",
        "QtXml",
    )

    # Also remove the large software OpenGL renderer
    remove_exact = {"opengl32sw.dll"}

    for f in pyside6_dir.iterdir():
        if not f.is_file():
            continue
        name = f.name
        should_remove = False

        if name in remove_exact:
            should_remove = True
        elif f.suffix.lower() == ".dll" and any(name.startswith(p) for p in remove_dll_prefixes):
            should_remove = True
        elif f.suffix.lower() == ".pyd" and any(name.startswith(p) for p in remove_pyd_prefixes):
            should_remove = True

        if should_remove:
            removed_size += f.stat().st_size
            f.unlink()

    # Plugins: remove unused plugin directories
    plugins_dir = pyside6_dir / "plugins"
    if plugins_dir.exists():
        keep_plugin_dirs = {"iconengines", "imageformats", "platforms", "styles", "tls", "networkinformation"}
        for plugin_dir in list(plugins_dir.iterdir()):
            if plugin_dir.is_dir() and plugin_dir.name not in keep_plugin_dirs:
                size = sum(f.stat().st_size for f in plugin_dir.rglob("*") if f.is_file())
                shutil.rmtree(plugin_dir, ignore_errors=True)
                removed_size += size

        # Remove PDF plugin from imageformats (not needed)
        pdf_plugin = plugins_dir / "imageformats" / "qpdf.dll"
        if pdf_plugin.exists():
            removed_size += pdf_plugin.stat().st_size
            pdf_plugin.unlink()

    # Remove subdirectories that are not needed at runtime
    for dirname in ("qml", "resources", "translations", "typesystems"):
        d = pyside6_dir / dirname
        if d.exists():
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d, ignore_errors=True)
            removed_size += size

    # Remove executables we don't need (designer, linguist, assistant, etc.)
    for f in pyside6_dir.glob("*.exe"):
        removed_size += f.stat().st_size
        f.unlink()

    print(f"  Removed {removed_size / 1024 / 1024:.1f} MB of unused PySide6 modules")
    return removed_size


def cleanup_dist(lib_dir):
    """Remove unnecessary files from the distribution to reduce size."""
    print("  Cleaning up distribution...")
    removed_size = 0

    patterns_to_remove = [
        # Python cache files
        "**/__pycache__",
        # Test directories: only for known-safe packages (a blanket **/test* delete can break packages
        # that import from a "test" module at runtime)
        *[f"{pkg}/tests" for pkg in SAFE_TEST_DIR_PACKAGES],
        # Documentation
        "**/*.md",
        "**/*.rst",
        # NOTE: dist-info LICENSE/NOTICE/AUTHORS files and licenses/ dirs are intentionally kept
        # (license compliance for redistributed third-party packages).
        # Type stubs (not needed at runtime)
        "**/*.pyi",
        # Pip itself (not needed at runtime)
        "pip",
        "pip-*",
    ]

    for pattern in patterns_to_remove:
        for path in lib_dir.glob(pattern):
            if path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                shutil.rmtree(path, ignore_errors=True)
                removed_size += size
            elif path.is_file():
                removed_size += path.stat().st_size
                path.unlink(missing_ok=True)

    # Trim PySide6 (biggest win)
    removed_size += trim_pyside6(lib_dir)

    print(f"  Total removed: {removed_size / 1024 / 1024:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="Build FastFlix distribution")
    parser.add_argument("--python-version", default=DEFAULT_PYTHON_VERSION, help="Python version to embed")
    parser.add_argument("--arch", default=None, help="Architecture: amd64 or arm64")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--archive", action="store_true", help="Create tar.zst archive for installer embedding")
    parser.add_argument(
        "--installer", action="store_true", help="Also build dist/FastFlix_installer.exe (implies --archive)"
    )
    parser.add_argument("--skip-download", action="store_true", help="Use cached downloads only")
    args = parser.parse_args()

    arch = args.arch or detect_arch()
    if arch not in ("amd64", "arm64"):
        parser.error("--arch must be amd64 or arm64")
    if args.installer:
        args.archive = True
    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "dist" / "FastFlix"

    print("Building FastFlix distribution")
    print(f"  Python: {args.python_version}")
    print(f"  Architecture: {arch}")
    print(f"  Output: {output_dir}")
    print()

    # Clean output directory
    if output_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(output_dir)

    python_dir = output_dir / "python"
    lib_dir = output_dir / "lib"

    # Step 1: Download embeddable Python
    print("[1/6] Downloading embeddable Python...")
    python_zip = CACHE_DIR / f"python-{args.python_version}-embed-{arch}.zip"
    if not python_zip.exists() and not args.skip_download:
        download_file(get_python_url(args.python_version, arch), python_zip)
    elif not python_zip.exists():
        print(f"  ERROR: {python_zip} not found and --skip-download is set")
        sys.exit(1)
    else:
        print(f"  Using cached {python_zip.name}")

    # Step 2: Extract Python
    print("[2/6] Extracting Python...")
    extract_python(python_zip, python_dir)

    # Step 3: Configure ._pth file
    print("[3/6] Configuring Python path...")
    configure_pth_file(python_dir)

    # Step 4: Bootstrap pip
    print("[4/6] (pip bootstrap not needed)")

    # Step 5: Install dependencies
    print("[5/6] Installing FastFlix and dependencies...")
    install_dependencies(lib_dir, PROJECT_ROOT, args.python_version, arch)

    # Step 6: Build Go launcher
    print("[6/7] Building Go launcher...")
    build_go_launcher(output_dir)

    # Step 7: Finalize
    print("[7/7] Finalizing distribution...")
    copy_data_files(output_dir, PROJECT_ROOT)
    cleanup_dist(lib_dir)

    # Calculate total size
    total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
    print(f"\nDistribution complete: {total_size / 1024 / 1024:.1f} MB total")
    print(f"Output: {output_dir}")

    # Optionally create archive for installer embedding
    if args.archive:
        print("Preparing installer resources...")
        prepare_installer_resources()
        archive_path = PROJECT_ROOT / "cmd" / "installer" / "fastflix_dist.tar.zst"
        create_dist_archive(output_dir, archive_path)

    if args.installer:
        print("Building installer...")
        build_go_installer(PROJECT_ROOT / "dist" / "FastFlix_installer.exe")


if __name__ == "__main__":
    main()
