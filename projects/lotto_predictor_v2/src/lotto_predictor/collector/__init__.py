"""Frontend Dev 동행복권 회차 수집기 모듈 공개 API.

상위 소비자(회차 데이터 로컬 캐시 저장소 등)는 본 패키지가 노출하는
심볼만 import 해야 한다. 내부 구현 파일(`core.py`, `models.py`)을
직접 참조하지 않는다.
"""

from .core import DrawFetcher, LottoCollector
from .models import (
    CollectorConfig,
    FailureReason,
    FetchFailure,
    StoppedReason,
    SyncResult,
)

__all__ = [
    "CollectorConfig",
    "DrawFetcher",
    "FailureReason",
    "FetchFailure",
    "LottoCollector",
    "StoppedReason",
    "SyncResult",
]
