# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import toml

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

a = Analysis(['fastflix\\__main__.py'],
             binaries=[],
             datas=[('iso-639-3.tab', 'iso639'), ('iso-639-3.json', 'iso639'), ('CHANGES', 'fastflix\\.'), ('docs\\build-licenses.txt', 'docs')] + all_fastflix_files,
             hiddenimports=all_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=["pyinstaller", "pypiwin32"],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='FastFlix',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=True,
          icon='fastflix\\data\\icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='FastFlix')
