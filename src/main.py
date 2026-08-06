"""ASGI entrypoint for Vercel (auto-detected as ``src/main.py``).

Vercel's native FastAPI runtime loads this file without putting ``src/`` on
``PYTHONPATH``, so prepend it before importing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from vivecaribe.main import app

__all__ = ["app"]
