"""Keep docs/API.md in step with the code."""

import importlib
import os
import re
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).parent.parent
PACKAGE = ROOT / "src" / "nightreign_boss_timer"
SECTION = re.compile(r"^### `(nightreign_boss_timer[\w.]*)`$")
# The first cell of a table row: `name`, `name(arguments)` or `Class.name(arguments)`.
ROW = re.compile(r"^\| `([A-Za-z_][\w.]*)(?:\([^`]*\))?` \|")
SCRIPT = re.compile(r"^\| `([\w./-]+\.py)` \|")


def sections() -> dict[str, list[str]]:
    """Module name to the names listed in its table."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in (ROOT / "docs" / "API.md").read_text(encoding="utf-8").splitlines():
        heading = SECTION.match(line)
        if heading:
            current = found.setdefault(heading.group(1), [])
        elif line.startswith("#"):
            current = None
        elif current is not None and (row := ROW.match(line)):
            current.append(row.group(1))
    return found


def modules() -> list[str]:
    names = []
    for path in sorted(PACKAGE.rglob("*.py")):
        parts = path.relative_to(PACKAGE.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            continue
        names.append(".".join(parts))
    return names


def test_every_module_has_a_section() -> None:
    documented = set(sections())
    assert [name for name in modules() if name not in documented] == []
    assert sorted(documented - set(modules()) - {"nightreign_boss_timer.i18n"}) == []


def test_every_section_lists_something() -> None:
    assert [module for module, names in sections().items() if not names] == []


@pytest.mark.skipif(sys.platform != "win32", reason="capture and the UI import only on Windows")
def test_every_documented_name_exists() -> None:
    missing = []
    for module_name, names in sections().items():
        module = importlib.import_module(module_name)
        for name in names:
            target = module
            try:
                for part in name.split("."):
                    target = getattr(target, part)
            except AttributeError:
                # Fields of a dataclass with slots are found on the class; plain instance
                # attributes set in __init__ are not, so look for them in the source.
                source = Path(module.__file__).read_text(encoding="utf-8")
                if f"self.{name.split('.')[-1]} " not in source:
                    missing.append(f"{module_name}: {name}")
    assert missing == []


def test_listed_scripts_exist() -> None:
    text = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    scripts = [m.group(1) for line in text.splitlines() if (m := SCRIPT.match(line))]
    assert len(scripts) >= 4
    assert [script for script in scripts if not (ROOT / script).is_file()] == []
