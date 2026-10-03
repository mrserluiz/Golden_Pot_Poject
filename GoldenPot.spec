# -*- mode: python ; coding: utf-8 -*-

import base64
import sys
from pathlib import Path


project_root = Path(SPECPATH)
sys.path.insert(0, str(project_root / "src"))
from golden_pot.branding import ICON_ICO_BASE64

icon_path = project_root / "build_icon.ico"
icon_path.write_bytes(base64.b64decode(ICON_ICO_BASE64))

a = Analysis(
    [str(project_root / "golden_pot_launcher.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[],
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
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "golden_pot_launcher.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[],
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
)
