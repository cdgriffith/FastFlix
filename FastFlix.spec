# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['fastflix/gui.py'],
             pathex=['/mnt/c/Users/Chris/PycharmProjects/FastFlix'],
             binaries=[],
             datas=[('fastflix/data/encoders/*', 'fastflix/data/encoders'), ('fastflix/data/rotations/*', 'fastflix/data/rotations'), ('fastflix/data/icon.ico', 'fastflix/data'), ('CHANGES', 'fastflix/.'), ('docs/build-licenses.txt', 'docs')],
             hiddenimports=['pyqt5', 'requests', 'python-box', 'reusables', 'pkg_resources.py2_warn'],
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
          console=True , icon='fastflix/data/icon.ico')
