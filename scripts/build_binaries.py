"""Build standalone RoXX binaries with PyInstaller."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "bin"
BUILD_DIR = ROOT / "build" / "pyinstaller"


def build_binary(entry_script: str, name: str) -> None:
    args = [
        str(ROOT / entry_script),
        "--name",
        name,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR / name),
        "--specpath",
        str(BUILD_DIR / "spec"),
        "--collect-data",
        "roxx",
        "--collect-submodules",
        "roxx",
        "--collect-submodules",
        "fido2",
        "--collect-submodules",
        "onelogin",
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
    ]
    PyInstaller.__main__.run(args)


def main() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    build_binary("roxx/__main__.py", "roxx")
    build_binary("roxx/cli/server.py", "roxx-server")
    build_binary("roxx/cli/setup.py", "roxx-setup")

    if platform.system() == "Windows":
        build_binary("roxx/cli/windows_service.py", "roxx-windows-service")


if __name__ == "__main__":
    main()

