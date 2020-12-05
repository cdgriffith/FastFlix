# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

all_fastflix_files = []

for root, dirs, files in os.walk('fastflix'):
	if "__pycache__" in root:
	    continue
	for file in files:
		all_fastflix_files.append((os.path.join(root,file), root))

a = Analysis(['fastflix\\__main__.py'],
             binaries=[],
             datas=[('iso-639-3.tab', 'iso639'), ('CHANGES', 'fastflix\\.'), ('docs\\build-licenses.txt', 'docs')] + all_fastflix_files,
             hiddenimports=['ruamel.yaml.SafeLoader', 'pyqt5', 'requests', 'python-box', 'reusables', 'pkg_resources.py2_warn', 'psutil', 'iso639', 'fastflix.models.config'],
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
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , icon='fastflix\\data\\icon.ico')
