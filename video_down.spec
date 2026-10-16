# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules


imageio_datas, imageio_binaries, imageio_hidden = collect_all("imageio_ffmpeg")
hidden_imports = (
    imageio_hidden
    + collect_submodules("yt_dlp.extractor")
    + collect_submodules("yt_dlp.postprocessor")
    + collect_submodules("you_get.extractors")
    + collect_submodules("you_get.processor")
)

a = Analysis(
    ["windows_entry.py"],
    pathex=[],
    binaries=imageio_binaries,
    datas=imageio_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="video_down",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    hide_console="hide-early",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
