# Third-Party Licenses

Parrot's own source code is distributed under the MIT license (see
`LICENSE`). This app depends on third-party libraries under their own
licenses. The vast majority are permissive (MIT, BSD-2/3-Clause, Apache-2.0,
PSF, HPND, Unlicense, file-level MPL-2.0) and impose no obligation beyond
preserving their copyright notice — no action needed for those.

This file specifically documents the copyleft (LGPL/GPL) components present
in the environment installed by `requirements.txt`, why they're there, and
what that implies.

## LGPL/GPL components

### pystray (LGPL-3.0)
- **Use**: system tray icon (`tray_icon.py`, direct `import pystray`).
- **How it's used**: imported as a Python package without modifying its
  source. Under LGPL, this is equivalent to traditional "dynamic linking":
  the end user can replace the installed version (`pip install
  pystray==<other version>`) without touching Parrot's code. Parrot's own
  code does not need to be released under LGPL/GPL.

### lameenc (LGPL-3.0)
- **Origin**: transitive dependency of `demucs` (used by Demucs for its own
  `--mp3` option, which Parrot **does not** invoke — `services/separator.py`
  always requests `.wav` output). It still gets installed into the
  environment regardless, even though Parrot never exercises that code path.
- No modifications to `lameenc`'s code; used as published on PyPI.

### av / PyAV (own code: BSD-3-Clause; FFmpeg binaries bundled in the wheel: GPL)
- **Origin**: required dependency of `faster-whisper` (used in
  `services/transcriber.py` for Whisper transcription).
- **Relevant finding from this audit**: PyAV's Python/Cython code is
  BSD-3-Clause, but the official wheel downloaded from PyPI ships **its own
  pre-compiled FFmpeg libraries** (`libavcodec`, `libavformat`, etc.),
  separate from the ffmpeg Parrot downloads/manages in
  `launcher.py::ensure_ffmpeg()`. That FFmpeg build bundled with PyAV
  includes `libx264` and `libx265` (video encoders licensed under GPL, with
  no LGPL variant), something PyPI/pip metadata doesn't declare (`pip show
  av` reports BSD-3-Clause) — detected by inspecting the actual installed
  binaries (`site-packages/av/.dylibs/`).
- **Why this doesn't change the decision to build our own LGPL ffmpeg**:
  these are two completely separate FFmpeg binaries. The one compiled by
  `release.yml`/downloaded by `ensure_ffmpeg()` is the one invoked by
  `services/separator.py` and `services/mixer.py` (via `ffmpeg-python`,
  subprocess calls to the `ffmpeg`/`ffprobe` executable) — that one is 100%
  LGPL by deliberate choice. PyAV's copy lives embedded inside the `av`
  package and is only used internally by `faster-whisper` to decode audio;
  Parrot never invokes its video encoders.
- **Why it's documented anyway, without blocking the release**: Parrot
  doesn't compile or redistribute that binary itself — it's downloaded fresh
  from PyPI at install time (`pip install -r requirements.txt`, inside
  `run_install_with_gui`). The PyAV project builds and publishes that wheel,
  and is responsible for its own GPL compliance (FFmpeg's source is publicly
  available at ffmpeg.org, and PyAV's build scripts are public on GitHub).
  This is the same pattern as any Linux distribution/package manager: each
  package keeps its own license, and whoever adds the dependency documents
  and attributes it rather than re-hosting a third party's source.

## Remaining dependencies (permissive, no action required)

MIT, BSD-2/3-Clause, Apache-2.0, PSF License, HPND (Pillow), Unlicense
(filelock), file-level MPL-2.0 (certifi, tqdm) — includes, among others:
`torch`, `torchaudio`, `demucs`, `dora_search`, `openunmix`, `faster-whisper`,
`ctranslate2`, `fastapi`, `starlette`, `uvicorn`, `pydantic`, `numpy`,
`ffmpeg-python`, `huggingface_hub`, `onnxruntime`, `Pillow`, `PyYAML`, `rich`,
`click`, `Jinja2`. Full, exact list reproducible with:

```
pip install pip-licenses
pip-licenses --format=plain
```

## External binary: ffmpeg/ffprobe

Not a pip dependency: it's an executable that
`launcher.py::ensure_ffmpeg()` downloads separately (or uses the system's, if
already present) and prepends to `main.py`'s process `PATH`. See
`SMART_LAUNCHER.txt` (section O) for the full detail on sources and licensing
(self-built LGPL for macOS, LGPL BtbN/FFmpeg-Builds for Windows/Linux).
