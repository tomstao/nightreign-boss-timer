"""The pieces a packaged program depends on. The build itself runs in its own CI job."""

import importlib.util
import logging
import sys
from pathlib import Path

import pytest

from nightreign_boss_timer import ocr

ROOT = Path(__file__).parent.parent
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="packaging is Windows-only")


@pytest.fixture(scope="module")
def build_exe() -> object:
    """The build script, loaded as a module without running a build."""
    spec = importlib.util.spec_from_file_location("build_exe", ROOT / "tools" / "build_exe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_packages_are_what_the_program_needs(build_exe: object) -> None:
    names = {name.lower().replace("_", "-") for name in build_exe.runtime_packages()}
    assert {"nightreign-boss-timer", "numpy", "onnxruntime", "pyside6-essentials"} <= names
    assert "shiboken6" in names  # a dependency of a dependency
    # Tools used only to develop and build are not packed in, so their licences are not needed.
    assert names.isdisjoint({"pytest", "ruff", "pyinstaller", "pre-commit"})


def test_licences_of_everything_packed_are_collected(build_exe: object, tmp_path: Path) -> None:
    count = build_exe.copy_licences(tmp_path)
    names = {path.name for path in tmp_path.iterdir()}
    assert count == len(names)  # no file overwrote another
    # Qt for Python ships no LGPL text of its own, so the standard texts are added.
    assert {"LGPL-3.0.txt", "GPL-3.0.txt", "Apache-2.0.txt"} <= names
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (tmp_path / "LGPL-3.0.txt").read_text("utf-8")
    assert any(name.startswith("onnxruntime-") for name in names)
    assert any(name.startswith("numpy-") for name in names)
    assert "nightreign-boss-timer-LICENSE" in names
    assert "Python-LICENSE.txt" in names
    assert not any(name.endswith((".dll", ".pyd", ".py")) for name in names)


def test_files_the_build_copies_exist(build_exe: object) -> None:
    for name in (
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "packaging/README.txt",
        "packaging/launcher.py",
    ):
        assert (ROOT / name).is_file(), name
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for component in ("PySide6", "NumPy", "ONNX Runtime", "PP-OCRv6", "PyInstaller", "Python"):
        assert component in notices, component


def test_unused_files_are_removed_from_a_built_folder(build_exe: object, tmp_path: Path) -> None:
    qt = tmp_path / "_internal" / "PySide6"
    (qt / "translations").mkdir(parents=True)
    (qt / "translations" / "qt_de.qm").write_bytes(b"x")
    (qt / "opengl32sw.dll").write_bytes(b"x")
    (qt / "Qt6Core.dll").write_bytes(b"x")
    build_exe.remove_unused(tmp_path)
    build_exe.remove_unused(tmp_path)  # running it twice is harmless
    assert [path.name for path in qt.iterdir()] == ["Qt6Core.dll"]


def test_zip_holds_one_folder_named_after_the_program(
    build_exe: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import zipfile

    folder = tmp_path / "nightreign-boss-timer"
    (folder / "_internal").mkdir(parents=True)
    (folder / "nightreign-boss-timer.exe").write_bytes(b"exe")
    (folder / "_internal" / "data.bin").write_bytes(b"data")
    monkeypatch.setattr(build_exe, "DIST", tmp_path)
    archive = build_exe.make_zip(folder, "1.2.3")
    assert archive.name == "nightreign-boss-timer-1.2.3-windows.zip"
    with zipfile.ZipFile(archive) as packed:
        assert sorted(packed.namelist()) == [
            "nightreign-boss-timer/_internal/data.bin",
            "nightreign-boss-timer/nightreign-boss-timer.exe",
        ]


def test_packed_model_is_preferred_in_a_packaged_program(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NBT_MODEL_DIR", raising=False)
    assert ocr.bundled_model_path() is None  # running from source

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    packed = tmp_path / "models" / ocr.MODEL_NAME
    assert ocr.bundled_model_path() == packed
    assert ocr.default_model_path() != packed  # not there: fall back to the downloaded copy
    packed.parent.mkdir()
    packed.write_bytes(b"model")
    assert ocr.default_model_path() == packed

    monkeypatch.setenv("NBT_MODEL_DIR", str(tmp_path / "elsewhere"))
    assert ocr.default_model_path() == tmp_path / "elsewhere" / ocr.MODEL_NAME  # still wins


def test_self_test_starts_everything_and_touches_no_real_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.ui import app as app_module

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    application = QApplication.instance() or QApplication([])
    app_module.start_logging()
    try:
        assert app_module.self_test(application) == 0
    finally:
        for handler in list(app_module.log.handlers):
            handler.close()
            app_module.log.removeHandler(handler)
        sys.excepthook = sys.__excepthook__

    log = (tmp_path / "local" / "nightreign-boss-timer" / "logs" / "app.log").read_text("utf-8")
    assert "Self-test passed" in log
    # The self-test used its own temporary settings, not the user's.
    assert not settings_file.default_settings_path().exists()
    assert logging.getLogger("nightreign_boss_timer").level == logging.INFO
