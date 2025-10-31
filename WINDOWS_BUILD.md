# Building FastFlix on Windows

This guide explains how to build FastFlix executables on Windows.

## Prerequisites

1. **Python 3.12 or higher**
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Git** (to clone/update the repository)
   - Download from [git-scm.com](https://git-scm.com/download/win)

## Build Steps

### 1. Open Command Prompt or PowerShell

Navigate to where you want to clone/have the FastFlix repository:

```bash
cd C:\path\to\your\projects
git clone https://github.com/cdgriffith/FastFlix.git
cd FastFlix
```

Or if you already have it:

```bash
cd C:\path\to\FastFlix
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your command prompt.

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs FastFlix in editable mode with all development dependencies including PyInstaller.

### 4. Build the Executable

You have two options:

#### Option A: Single Executable (Recommended for distribution)

```bash
pyinstaller FastFlix_Windows_OneFile.spec
```

The executable will be in: `dist\FastFlix.exe`

#### Option B: Directory with Multiple Files (Faster startup)

```bash
pyinstaller FastFlix_Windows_Installer.spec
```

The executable will be in: `dist\FastFlix\FastFlix.exe`

### 5. Test the Build

```bash
cd dist
FastFlix.exe
```

Or for the installer version:

```bash
cd dist\FastFlix
FastFlix.exe
```

## Running Without Building (For Testing)

If you just want to test changes without building an executable:

```bash
python -m fastflix
```

## Troubleshooting

### Missing Dependencies

If you get import errors, try reinstalling:

```bash
pip install --upgrade --force-reinstall -e ".[dev]"
```

### Build Errors

1. Make sure you're in the FastFlix root directory
2. Ensure the virtual environment is activated (you see `(venv)`)
3. Try deleting `build` and `dist` folders and rebuilding:

```bash
rmdir /s /q build dist
pyinstaller FastFlix_Windows_OneFile.spec
```

### FFmpeg Not Found

The FastFlix executable doesn't include FFmpeg. You need to:

1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. Extract it somewhere
3. Add the `bin` folder to your PATH, or configure it in FastFlix settings

## Known Limitations

### PGS to SRT OCR (PyInstaller builds)

Due to an upstream issue in pgsrip v0.1.12, PGS to SRT OCR conversion does not work in PyInstaller-built executables. The feature works perfectly when running from source (`python -m fastflix`).

If you need PGS OCR functionality, please run FastFlix from source instead of using the compiled executable.

## Notes

- The build process creates a `portable.py` file temporarily (it's removed after)
- The `.spec` files automatically collect all dependencies from `pyproject.toml`
- The icon is located at `fastflix\data\icon.ico`
