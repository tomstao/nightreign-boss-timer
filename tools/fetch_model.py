"""Download the text recognition model and check it is the expected file.

    uv run python tools/fetch_model.py

The model (about 21 MB) is PP-OCRv6 "small" from the PaddleOCR project, in the ONNX form published
by RapidOCR, both under the Apache 2.0 licence. It is saved outside the repository.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request

from nightreign_boss_timer.ocr import MODEL_SHA256, MODEL_URL, default_model_path


def sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    target = default_model_path()
    if target.exists() and sha256(target) == MODEL_SHA256:
        print(f"Model already present: {target}")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    print(f"Downloading {MODEL_URL}")
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "nightreign-boss-timer"})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)

    found = sha256(partial)
    if found != MODEL_SHA256:
        partial.unlink()
        print(f"Checksum mismatch: expected {MODEL_SHA256}, got {found}. Nothing was kept.")
        return 1
    partial.replace(target)
    print(f"Saved and verified: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
