"""Build the Windows program and the ZIP that is published as a release.

    uv run python tools/fetch_model.py      # once: the text model is packed into the program
    uv run python tools/build_exe.py

The result is the folder ``dist/nightreign-boss-timer/``, holding ``nightreign-boss-timer.exe`` and
everything it needs, its own Python included, and the same folder packed as
``dist/nightreign-boss-timer-<version>-windows.zip``.
The freshly built program is started once with ``--self-test`` and the build fails if that fails.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from importlib import metadata
from pathlib import Path

import PyInstaller.__main__

from nightreign_boss_timer.ocr import MODEL_NAME, default_model_path

NAME = "nightreign-boss-timer"
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
# Pulled in by libraries for uses this program does not have. Leaving them out keeps it small.
EXCLUDED = ("tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtOpenGL")


def runtime_packages() -> list[str]:
    """This project's runtime dependencies and theirs, by distribution name."""
    seen: dict[str, None] = {}
    waiting = [NAME]
    while waiting:
        name = waiting.pop()
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # an optional dependency that is not installed
        key = distribution.metadata["Name"]
        if key in seen:
            continue
        seen[key] = None
        for requirement in distribution.requires or []:
            if "extra ==" in requirement:
                continue
            # "numpy>=2.0; python_version > '3.10'" -> "numpy"
            for stop in " ;<>=!~[(":
                requirement = requirement.split(stop, 1)[0]
            waiting.append(requirement)
    return sorted(seen, key=str.casefold)


# Files that come with Qt and that this program never uses. Removing them saves about 27 MB.
UNUSED = (
    "PySide6/opengl32sw.dll",  # software 3D drawing, for programs that draw with OpenGL
    "PySide6/translations",  # Qt's own dialog texts; this program has its own translations
)
_LICENCE_WORDS = ("licen", "copying", "notice")
_LICENCE_ENDINGS = ("", ".txt", ".md", ".rst", ".apache", ".bsd", ".mit")


def copy_licences(target: Path) -> int:
    """Put the licence files of everything packed into the program next to it.

    Three sources: the licence files each library ships, the standard licence texts kept in
    ``packaging/licenses`` for libraries whose package leaves them out (Qt for Python ships
    none of the LGPL), and the licence of Python itself.
    """
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in runtime_packages():
        distribution = metadata.distribution(name)
        for file in distribution.files or []:
            wanted = any(word in file.name.lower() for word in _LICENCE_WORDS)
            if not wanted or file.suffix.lower() not in _LICENCE_ENDINGS:
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                # Several files of one library can share a name, so keep the folders in it.
                inner = [part for part in file.parts[:-1] if not part.endswith(".dist-info")]
                inner = [part for part in inner if part not in ("licenses", name)]
                copy = target / "-".join([name, *inner, file.name])
                if not copy.exists():  # some libraries ship the same licence file twice
                    shutil.copyfile(source, copy)
                    copied += 1
    for source in sorted((ROOT / "packaging" / "licenses").glob("*.txt")):
        shutil.copyfile(source, target / source.name)
        copied += 1
    python_licence = Path(sys.base_prefix) / "LICENSE.txt"
    if python_licence.is_file():
        shutil.copyfile(python_licence, target / "Python-LICENSE.txt")
        copied += 1
    return copied


def remove_unused(folder: Path) -> None:
    for name in UNUSED:
        path = folder / "_internal" / name
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def build(folder: Path) -> None:
    model = default_model_path()
    if not model.exists():
        raise SystemExit(f"{MODEL_NAME} is missing. Run: uv run python tools/fetch_model.py")
    arguments = [
        str(ROOT / "packaging" / "launcher.py"),
        f"--name={NAME}",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",  # no console window behind the tray icon
        f"--paths={ROOT / 'src'}",
        f"--collect-data={NAME.replace('-', '_')}",  # the translation files
        f"--copy-metadata={NAME}",  # so the program knows its own version
        f"--add-data={model}{';' if sys.platform == 'win32' else ':'}models",
        f"--distpath={DIST}",
        f"--workpath={ROOT / 'build' / 'work'}",
        f"--specpath={ROOT / 'build'}",
    ]
    arguments += [f"--exclude-module={module}" for module in EXCLUDED]
    PyInstaller.__main__.run(arguments)

    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copyfile(ROOT / name, folder / name)
    shutil.copyfile(ROOT / "packaging" / "README.txt", folder / "README.txt")
    print(f"Copied {copy_licences(folder / 'licenses')} licence files")
    remove_unused(folder)


def self_test(folder: Path) -> None:
    """Start the built program once. It checks itself and exits; anything but 0 is a failure."""
    result = subprocess.run([str(folder / f"{NAME}.exe"), "--self-test"], timeout=120, check=False)
    if result.returncode != 0:
        raise SystemExit(f"The built program failed its self-test (exit code {result.returncode})")
    print("Self-test passed")


def make_zip(folder: Path, version: str) -> Path:
    archive = DIST / f"{NAME}-{version}-windows.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                packed.write(path, Path(NAME) / path.relative_to(folder))
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-zip", action="store_true", help="build the folder only")
    parser.add_argument("--no-self-test", action="store_true", help="do not start the result")
    args = parser.parse_args()

    version = metadata.version(NAME)
    folder = DIST / NAME
    build(folder)
    if not args.no_self_test:
        self_test(folder)
    size = sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())
    print(f"Built {folder} ({size / 1e6:.0f} MB)")
    if not args.no_zip:
        archive = make_zip(folder, version)
        print(f"Packed {archive} ({archive.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
