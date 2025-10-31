# -*- mode: python ; coding: utf-8 -*-
import os
import toml

from PyInstaller.utils.hooks import collect_submodules, copy_metadata, collect_data_files

block_cipher = None

all_fastflix_files = []

for root, dirs, files in os.walk('fastflix'):
	if "__pycache__" in root:
	    continue
	for file in files:
		all_fastflix_files.append((os.path.join(root,file), root))

all_imports = collect_submodules('pydantic') + ['dataclasses', 'colorsys', 'typing_extensions', 'box']

with open("pyproject.toml") as f:
    for line in toml.load(f)["project"]["dependencies"]:
        package = line.split("[")[0].split("=")[0].split(">")[0].split("<")[0].replace('"', '').replace("'",'').rstrip("~").strip()
        if package not in ("pyinstaller"):
            all_imports.append(package)

all_imports.remove("iso639-lang")
all_imports.remove("python-box")
all_imports.append("box")
all_imports.append("iso639")

# Add pgsrip for OCR support
all_imports.extend(["pgsrip", "pytesseract", "cv2", "numpy", "pysrt", "babelfish", "babelfish.converters", "babelfish.converters.alpha2", "babelfish.converters.alpha3b", "babelfish.converters.alpha3t", "babelfish.converters.name", "babelfish.converters.opensubtitles", "cleanit"])

portable_file = "fastflix\\portable.py"
with open(portable_file, "w") as portable:
    portable.write(" ")

a = Analysis(['fastflix\\__main__.py'],
             binaries=[],
             datas=[('CHANGES', 'fastflix\\.'), ('docs\\build-licenses.txt', 'docs')] + all_fastflix_files + copy_metadata('pgsrip') + copy_metadata('pytesseract') + copy_metadata('babelfish') + copy_metadata('cleanit') + copy_metadata('trakit') + collect_data_files('babelfish') + collect_data_files('cleanit'),
             hiddenimports=all_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='FastFlix',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          icon='fastflix\\data\\icon.ico')

os.unlink(portable_file)
