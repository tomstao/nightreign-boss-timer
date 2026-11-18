# Third-party notices

nightreign-boss-timer itself is under the MIT licence (see `LICENSE`). The packaged program
contains the software and the model listed here. Each stays under its own licence, and the full
licence texts are in the `licenses` folder of the packaged program.

| Component | Used for | Licence |
|---|---|---|
| [Python](https://www.python.org/) | the language runtime | PSF License 2.0 |
| [Qt for Python (PySide6)](https://doc.qt.io/qtforpython-6/) and [Qt](https://www.qt.io/) | windows, overlay, tray icon | LGPL-3.0 |
| [NumPy](https://numpy.org/) | reading pixels | BSD-3-Clause |
| [ONNX Runtime](https://onnxruntime.ai/) and its dependencies | running the text recognition model | MIT, and others listed in the `licenses` folder |
| PP-OCRv6 "small" recognition model, from [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), in the ONNX form published by [RapidOCR](https://github.com/RapidAI/RapidOCR) | reading boss names | Apache-2.0 |
| [PyInstaller](https://pyinstaller.org/) bootloader | starting the packaged program | GPL-2.0-or-later with an exception that allows distributing programs built with it under any licence |

## Qt and the LGPL

Qt and PySide6 are used unmodified, as separate library files inside the program's `_internal`
folder (`PySide6\*.dll`, `PySide6\*.pyd`, `shiboken6\*`). You may replace those files with your
own builds of the same libraries. The source code of Qt is available from
<https://download.qt.io/official_releases/qt/>, and that of PySide6 from
<https://download.qt.io/official_releases/QtForPython/>.

## The text recognition model

The model file `PP-OCRv6_rec_small.onnx` is included unmodified. It is checked against a known
checksum when it is downloaded for packaging (`tools/fetch_model.py`).

## Not included

No game files, game assets or game code are part of this program. ELDEN RING NIGHTREIGN is a
trademark of its owners. This project is not affiliated with FromSoftware or Bandai Namco.
