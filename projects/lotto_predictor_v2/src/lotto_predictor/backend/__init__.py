"""Backend 레이어 공개 API.

상위 Frontend Dev 모듈(수집기, 캐시, 통계, 추천, 리포트)과 Game Logic Dev
도메인 계층은 본 패키지에서 공개한 심볼만 import 하도록 강제한다.
내부 구현 파일을 직접 import 하지 않는다.
"""

from .http_client import DhLotteryClient, ThreeTierLotteryClient
from .models import (
    BackendError,
    DrawNotFoundError,
    FetchCheckpoint,
    FetchResult,
    LottoDraw,
    NumberFrequencyRow,
    TransientFetchError,
)
from .serialization import parse_draw
from .storage import LottoStorage

__all__ = [
    "BackendError",
    "DhLotteryClient",
    "DrawNotFoundError",
    "FetchCheckpoint",
    "FetchResult",
    "LottoDraw",
    "LottoStorage",
    "NumberFrequencyRow",
    "ThreeTierLotteryClient",
    "TransientFetchError",
    "parse_draw",
]
