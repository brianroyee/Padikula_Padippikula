# PyInstaller build specification for Padikula, Padippikula.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH)
data_files = [
    (str(project_root / "config"), "config"),
    (str(project_root / "assets"), "assets"),
]
hiddenimports = [
    "pygame",
    "pygame.mixer",
    "psutil",
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "winotify",
    "pystray",
    "PIL",
]
hiddenimports.extend(collect_submodules("pygame"))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hiddenimports,
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
    name="Padikula_Padippikula",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
