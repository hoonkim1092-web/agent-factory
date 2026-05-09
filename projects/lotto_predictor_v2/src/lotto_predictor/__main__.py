"""PyInstaller onefile 엔트리 — `lotto.cli.main`에 위임.

test_pyinstaller_e2e.py의 계약이 `src/lotto_predictor/__main__.py`를 빌드 진입점으로
고정하고 있어, 실제 추천 파이프라인이 구현된 `lotto` 패키지로 연결한다.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """frozen 바이너리와 소스 양쪽에서 `lotto` 패키지를 import 가능하게 한다."""
    here = Path(__file__).resolve().parent  # .../src/lotto_predictor
    src_root = here.parent                   # .../src
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_ensure_src_on_path()

from lotto.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
