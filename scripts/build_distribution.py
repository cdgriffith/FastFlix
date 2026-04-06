#!/usr/bin/env python3
"""
Build script for FastFlix distribution using embeddable Python.

Replaces PyInstaller by bundling the official Python embeddable distribution
with pip-installed dependencies. The output is a self-contained directory
that can be launched via the Go launcher.

Usage:
    python scripts/build_distribution.py [--python-version 3.13.1] [--arch amd64] [--output dist/FastFlix]

Requirements:
    - Internet access (downloads Python embeddable distribution and get-pip.py)
    - Or: pre-downloaded files in scripts/cache/
"""

import argparse
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "scripts" / "cache"


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


def get_pip_url():
    return "https://bootstrap.pypa.io/get-pip.py"


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


def bootstrap_pip(python_dir):
    """No longer needed — we use the system Python's pip to install into --target.

    Kept as a no-op for the build step numbering.
    """
    pass


def build_wheel(project_root):
    """Build a wheel of FastFlix using the system Python.

    The embeddable Python doesn't have setuptools in its build isolation
    environment, so we build the wheel with the system Python first.
    """
    wheel_dir = project_root / "dist" / "wheels"
    wheel_dir.mkdir(parents=True, exist_ok=True)

    print("  Building FastFlix wheel with system Python...")
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(project_root), "--wheel-dir", str(wheel_dir), "--no-deps"],
        check=True,
    )

    # Find the built wheel
    wheels = list(wheel_dir.glob("fastflix-*.whl"))
    if not wheels:
        print("  ERROR: No wheel built")
        sys.exit(1)
    return wheels[0]


def install_dependencies(python_dir, lib_dir, project_root):
    """Install FastFlix and all dependencies into the lib directory.

    Uses the SYSTEM Python's pip (not the embeddable one) to avoid build
    isolation issues. The --target flag installs everything into lib_dir.
    """
    lib_dir.mkdir(parents=True, exist_ok=True)

    # Build fastflix wheel with system Python
    wheel_path = build_wheel(project_root)

    # Install using system Python's pip with --target
    print("  Installing FastFlix wheel and dependencies...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(wheel_path),
            "--target",
            str(lib_dir),
            "--no-warn-script-location",
            "--no-cache-dir",
        ],
        check=True,
    )


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
    """Build the Go launcher binary and place it in the distribution."""
    from fastflix.version import __version__

    launcher_exe = output_dir / "FastFlix.exe"
    print(f"  Building launcher -> {launcher_exe}")
    subprocess.run(
        [
            "go",
            "build",
            f"-ldflags=-s -w -X main.Version={__version__}",
            "-o",
            str(launcher_exe),
            "./cmd/launcher",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    print(f"  Launcher built ({launcher_exe.stat().st_size / 1024 / 1024:.1f} MB)")

    # Build standalone uninstaller
    uninstaller_exe = output_dir / "uninstall.exe"
    print(f"  Building uninstaller -> {uninstaller_exe}")
    subprocess.run(
        [
            "go",
            "build",
            "-ldflags=-s -w",
            "-o",
            str(uninstaller_exe),
            "./cmd/uninstaller",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    print(f"  Uninstaller built ({uninstaller_exe.stat().st_size / 1024 / 1024:.1f} MB)")


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

    from fastflix.version import __version__

    timestamp = datetime.now().strftime("%Y.%m.%d-%H.%M")
    version_file.write_text(f"{__version__}-{branch}-{timestamp}")


def create_dist_archive(output_dir, archive_path):
    """Create a tar.zst archive of the distribution for the installer to embed.

    Uses Zstandard compression for better ratio than ZIP Deflate (~20-25% smaller)
    while maintaining fast decompression during installation.
    """
    import tarfile

    try:
        import zstandard
    except ImportError:
        print("  ERROR: zstandard package not installed. Run: pip install zstandard")
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
        # Test directories
        "**/tests",
        "**/test",
        # Documentation
        "**/*.md",
        "**/*.rst",
        # Dist-info extras (keep METADATA and RECORD)
        "**/*.dist-info/LICENSE*",
        "**/*.dist-info/NOTICE*",
        "**/*.dist-info/AUTHORS*",
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
    parser.add_argument("--python-version", default="3.13.1", help="Python version to embed")
    parser.add_argument("--arch", default=None, help="Architecture: amd64 or arm64")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--archive", action="store_true", help="Create tar.zst archive for installer embedding")
    parser.add_argument("--skip-download", action="store_true", help="Use cached downloads only")
    args = parser.parse_args()

    arch = args.arch or detect_arch()
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
    print("[4/6] Bootstrapping pip...")
    bootstrap_pip(python_dir)

    # Step 5: Install dependencies
    print("[5/6] Installing FastFlix and dependencies...")
    install_dependencies(python_dir, lib_dir, PROJECT_ROOT)

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


if __name__ == "__main__":
    main()
