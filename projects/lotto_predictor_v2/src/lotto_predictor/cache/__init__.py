"""Frontend Dev 회차 데이터 로컬 캐시 저장소 공개 API.

상위 소비자(통계 분석 엔진·추천기·리포트)는 본 패키지가 노출하는 심볼만
import 해야 한다. 내부 구현 파일(`core.py`, `models.py`)을 직접 참조하지 않는다.
"""

from .core import LottoDrawCache
from .models import (
    CacheAction,
    CacheConfig,
    CacheGapReport,
    CacheReadyResult,
    CacheStatus,
    RefreshPolicy,
    StaleReason,
)

__all__ = [
    "CacheAction",
    "CacheConfig",
    "CacheGapReport",
    "CacheReadyResult",
    "CacheStatus",
    "LottoDrawCache",
    "RefreshPolicy",
    "StaleReason",
]
