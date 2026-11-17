from pathlib import Path

import numpy as np
import pytest

from nightreign_boss_timer.ocr import (
    NameReader,
    _resize_to_height,
    default_model_path,
)

FIXTURES = Path(__file__).parent / "fixtures" / "name_regions.npz"

needs_model = pytest.mark.skipif(
    not default_model_path().exists(),
    reason="OCR model not downloaded; run tools/fetch_model.py",
)


@pytest.fixture(scope="module")
def reader() -> NameReader:
    return NameReader()


@pytest.fixture(scope="module")
def names() -> dict[str, np.ndarray]:
    """Boss name strips cut from real footage. See tests/fixtures/README.md."""
    with np.load(FIXTURES) as data:
        return {name: data[name] for name in data.files}


def test_resize_keeps_proportions() -> None:
    image = np.zeros((30, 448, 3), dtype=np.float32)
    assert _resize_to_height(image, 48).shape == (48, 717, 3)


def test_resize_of_a_flat_image_stays_flat() -> None:
    image = np.full((10, 20, 3), 0.25, dtype=np.float32)
    assert np.allclose(_resize_to_height(image, 48), 0.25)


def test_resize_caps_very_wide_lines() -> None:
    image = np.zeros((10, 4000, 3), dtype=np.float32)
    assert _resize_to_height(image, 48).shape[1] == 960


def test_missing_model_says_how_to_get_it(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="fetch_model"):
        NameReader(tmp_path / "missing.onnx")


def test_model_folder_can_be_overridden(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NBT_MODEL_DIR", str(tmp_path))
    assert default_model_path().parent == tmp_path


@needs_model
@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("clip_1080p_bar_appears", "黄金河马"),
        ("clip_1080p_mid_fight", "黄金河马"),
        ("screenshot_1440p", "神谕众使者"),
        ("screenshot_1440p_partly_hidden", "卡利亚禁卫骑士"),
    ],
)
def test_reads_real_boss_names(
    reader: NameReader, names: dict[str, np.ndarray], fixture: str, expected: str
) -> None:
    reading = reader.read(names[fixture])
    assert reading.text == expected
    assert reading.confidence > 0.9


@needs_model
def test_empty_strip_reads_nothing(reader: NameReader) -> None:
    assert reader.read(np.zeros((0, 0, 3), dtype=np.uint8)).text == ""


@needs_model
def test_blank_strip_reads_nothing(reader: NameReader) -> None:
    blank = np.full((30, 448, 3), 40, dtype=np.uint8)
    assert reader.read(blank).text == ""
