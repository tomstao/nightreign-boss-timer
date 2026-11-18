"""Read one line of text, the boss name, from a strip of pixels.

The name is always in the same place, so there is no text detection step: the strip goes straight
into a recognition model. The model is PP-OCRv6 "small" in ONNX form, which covers English,
Simplified Chinese and Traditional Chinese with one file. It runs on the CPU with one thread, so
it never competes with the game for the GPU, and it is only called a few times per fight.

The model file is not part of the repository. ``tools/fetch_model.py`` downloads it.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

MODEL_NAME = "PP-OCRv6_rec_small.onnx"
MODEL_URL = (
    "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv6/rec/"
    + MODEL_NAME
)
MODEL_SHA256 = "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884"

# The model takes lines scaled to this height.
_INPUT_HEIGHT = 48
_MAX_INPUT_WIDTH = 960


def bundled_model_path() -> Path | None:
    """The model packed into the packaged program, or None when running from source."""
    bundle = getattr(sys, "_MEIPASS", None)  # set by PyInstaller in a packaged program
    return Path(bundle) / "models" / MODEL_NAME if bundle else None


def default_model_path() -> Path:
    """Where the model is kept.

    ``NBT_MODEL_DIR`` if set, else the copy packed into the packaged program, else the
    user's local app data, where ``tools/fetch_model.py`` saves it.
    """
    folder = os.environ.get("NBT_MODEL_DIR")
    if folder:
        return Path(folder) / MODEL_NAME
    bundled = bundled_model_path()
    if bundled is not None and bundled.exists():
        return bundled
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "nightreign-boss-timer" / "models" / MODEL_NAME


@dataclass(frozen=True, slots=True)
class TextReading:
    """What the model read. ``confidence`` is the mean certainty of its characters, 0.0 to 1.0."""

    text: str
    confidence: float


def _resize_to_height(image: NDArray[np.float32], height: int) -> NDArray[np.float32]:
    """Bilinear resize of a (rows, columns, channels) image to a given height, keeping its shape."""
    rows, columns, _ = image.shape
    width = min(_MAX_INPUT_WIDTH, max(1, round(columns * height / rows)))
    ys = (np.arange(height) + 0.5) * rows / height - 0.5
    xs = (np.arange(width) + 0.5) * columns / width - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, rows - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, columns - 1)
    y1 = np.minimum(y0 + 1, rows - 1)
    x1 = np.minimum(x0 + 1, columns - 1)
    wy = np.clip(ys - y0, 0.0, 1.0)[:, None, None].astype(np.float32)
    wx = np.clip(xs - x0, 0.0, 1.0)[None, :, None].astype(np.float32)
    top = image[y0][:, x0] * (1 - wx) + image[y0][:, x1] * wx
    bottom = image[y1][:, x0] * (1 - wx) + image[y1][:, x1] * wx
    return top * (1 - wy) + bottom * wy


class NameReader:
    """Loads the model once and reads lines with :meth:`read`."""

    def __init__(self, model_path: Path | None = None) -> None:
        # Imported here so the rest of the package works without onnxruntime being loaded.
        import onnxruntime as ort

        path = model_path or default_model_path()
        if not path.exists():
            raise FileNotFoundError(
                f"OCR model not found at {path}. Run: uv run python tools/fetch_model.py"
            )
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._input = self._session.get_inputs()[0].name
        characters = self._session.get_modelmeta().custom_metadata_map["character"].splitlines()
        # Index 0 is the "nothing here" class, and the model's last class is a space.
        self._characters = ["", *characters, " "]

    def read(self, region: NDArray[np.uint8]) -> TextReading:
        """Read an RGB region of shape (rows, columns, 3) holding one line of text."""
        if region.size == 0:
            return TextReading("", 0.0)
        # The model was trained on blue-green-red images scaled to -1..1.
        image = region[..., ::-1].astype(np.float32) / 127.5 - 1.0
        image = _resize_to_height(image, _INPUT_HEIGHT)
        batch = np.ascontiguousarray(image.transpose(2, 0, 1)[None])
        (output,) = self._session.run(None, {self._input: batch})
        return self._decode(output[0])

    def _decode(self, steps: NDArray[np.float32]) -> TextReading:
        """Each step votes for a character. Drop repeats and "nothing here", keep the rest."""
        best = steps.argmax(axis=1)
        certainty = steps.max(axis=1)
        keep = (best != 0) & (best != np.concatenate([[0], best[:-1]]))
        text = "".join(self._characters[i] for i in best[keep])
        if not text.strip():
            return TextReading("", 0.0)
        return TextReading(text.strip(), float(certainty[keep].mean()))
