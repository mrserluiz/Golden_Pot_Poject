# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)
assets_path = project_root / "src" / "golden_pot" / "assets"
icon_path = assets_path / "icon1.ico"

a = Analysis(
    [str(project_root / "golden_pot_launcher.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[(str(assets_path), "golden_pot/assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GoldenPot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon_path),
)
