"""`lotto_predictor_v2.src` 경로를 `sys.path`에 주입한다.

서버 부팅과 테스트 초기화 시 1회 호출되며, 환경 변수
`LOTTO_PREDICTOR_SRC`가 지정되면 해당 경로를 우선 사용한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_RELATIVE = Path("projects") / "lotto_predictor_v2" / "src"
_bootstrapped = False


def _resolve_predictor_src() -> Path:
    configured = os.getenv("LOTTO_PREDICTOR_SRC")
    if configured:
        return Path(configured).expanduser().resolve()

    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / _DEFAULT_RELATIVE
        if candidate.is_dir():
            return candidate.resolve()

    repo_root = here.parents[2] if len(here.parents) >= 3 else here.parent
    return (repo_root / _DEFAULT_RELATIVE).resolve()


def ensure_predictor_importable() -> Path:
    """predictor_v2 소스 경로를 `sys.path`에 주입한다(중복 방지)."""
    global _bootstrapped
    src_path = _resolve_predictor_src()
    path_str = str(src_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    _bootstrapped = True
    return src_path


def smoke_import() -> None:
    """부팅 시 핵심 심볼 import 스모크 테스트.

    실패 시 RuntimeError를 올려 명확한 오류 메시지로 종료를 유도한다.
    """
    ensure_predictor_importable()
    try:
        import lotto.analytics.patterns  # noqa: F401
        import lotto.cache.store  # noqa: F401
        import lotto.recommender  # noqa: F401
    except ImportError as exc:  # pragma: no cover - 환경 문제 가드
        raise RuntimeError(
            "lotto_predictor_v2 모듈을 찾지 못했습니다. "
            "환경 변수 LOTTO_PREDICTOR_SRC로 경로를 지정하세요."
        ) from exc
