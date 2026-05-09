"""회차 데이터 로컬 캐시 저장소의 값 객체 정의.

Frontend Dev `frontend_dev_module_2` 스코프 문서
(`docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`) 에서 고정한 계약을 그대로
구현한다. 본 모듈은 규칙 검증이 아닌 "정책 설정"과 "상태 서술"만을 담당하며,
수집기/저장소 예외는 잡지 않고 호출자에게 전파한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from lotto_predictor.collector import SyncResult

# 신선도 판정 사유. `LottoDrawCache.status()` 가 열거해 `stale_reasons` 에 채운다.
StaleReason = Literal[
    "missing_checkpoint",
    "insufficient_draws",
    "expired_checkpoint",
    "unknown",
]

# `ensure_ready()` 가 실제로 어떤 경로를 탔는지 호출자에게 전달하는 라벨.
CacheAction = Literal["skipped", "synced", "offline"]

# 자동/수동 갱신 정책. "never" 이면 `ensure_ready` 가 수집 호출을 생략한다.
RefreshPolicy = Literal["auto", "never"]


@dataclass(frozen=True)
class CacheConfig:
    """캐시 신선도 판정과 갱신 정책을 제어하는 설정 묶음.

    - ``required_draws``: 최소 보유 회차 수. 부족하면 `is_stale=True` 이 되고
      `stale_reasons` 에 ``"insufficient_draws"`` 가 포함된다.
    - ``freshness_hours``: 체크포인트가 이 시간 이상 경과하면 만료로 간주한다.
    - ``refresh_policy``: ``"auto"`` 이면 필요 시 수집기를 위임 호출하고, ``"never"``
      이면 호출하지 않는다.
    - ``offline``: ``True`` 이면 수집 호출을 생략하고 저장된 데이터만 사용한다.
    """

    required_draws: int = 500
    freshness_hours: float = 24.0
    refresh_policy: RefreshPolicy = "auto"
    offline: bool = False

    def __post_init__(self) -> None:
        if self.required_draws <= 0:
            raise ValueError(
                f"required_draws 는 양의 정수여야 한다: {self.required_draws}"
            )
        if self.freshness_hours < 0:
            raise ValueError(
                f"freshness_hours 는 0 이상이어야 한다: {self.freshness_hours}"
            )
        if self.refresh_policy not in ("auto", "never"):
            raise ValueError(
                f"refresh_policy 는 'auto' 또는 'never' 여야 한다: {self.refresh_policy}"
            )


@dataclass(frozen=True)
class CacheStatus:
    """캐시 현재 상태 스냅샷.

    - ``total_draws`` 는 `LottoStorage` 에 저장된 회차 개수.
    - ``latest_drw_no`` / ``earliest_drw_no`` 는 저장된 회차 범위를 요약한다.
    - ``last_fetched_at`` 은 체크포인트의 ``fetched_at`` 값을 그대로 노출한다.
    - ``is_stale`` 은 `stale_reasons` 가 하나라도 있으면 ``True``.
    - ``stale_reasons`` 는 판정 사유 집합을 문자열 리터럴로 나열한다.
    """

    total_draws: int
    latest_drw_no: int | None
    earliest_drw_no: int | None
    last_fetched_at: datetime | None
    is_stale: bool
    stale_reasons: tuple[StaleReason, ...] = ()

    def __post_init__(self) -> None:
        if self.total_draws < 0:
            raise ValueError(
                f"total_draws 는 0 이상이어야 한다: {self.total_draws}"
            )
        if self.is_stale and not self.stale_reasons:
            raise ValueError(
                "is_stale=True 인데 stale_reasons 가 비어 있다 — 사유 집합이 누락됐다"
            )
        if (not self.is_stale) and self.stale_reasons:
            raise ValueError(
                "is_stale=False 인데 stale_reasons 가 존재한다 — 사유와 플래그가 어긋난다"
            )


@dataclass(frozen=True)
class CacheReadyResult:
    """`ensure_ready()` 호출 결과 묶음.

    - ``status`` 는 호출 후 갱신된 캐시 상태.
    - ``sync_result`` 는 실제 수집을 수행한 경우에만 채우고, 건너뛴 경우 ``None``.
    - ``action`` 은 실행 경로 분기(`"skipped" | "synced" | "offline"`).
    """

    status: CacheStatus
    action: CacheAction
    sync_result: SyncResult | None = None

    def __post_init__(self) -> None:
        if self.action == "synced" and self.sync_result is None:
            raise ValueError(
                "action='synced' 인데 sync_result 가 없다 — 수집 결과가 누락됐다"
            )
        if self.action != "synced" and self.sync_result is not None:
            raise ValueError(
                "sync_result 는 action='synced' 일 때만 채운다"
            )


@dataclass(frozen=True)
class CacheGapReport:
    """`validate_continuity()` 의 결과.

    - ``expected_range`` 는 `(earliest, latest)` 회차 구간. 저장소가 비어 있으면 ``None``.
    - ``missing_draws`` 는 구간 내 누락된 회차 번호(오름차순, 중복 없음).
    - ``is_continuous`` 는 구간이 완전 연속이면 ``True``.
    """

    expected_range: tuple[int, int] | None
    missing_draws: tuple[int, ...] = field(default_factory=tuple)
    is_continuous: bool = True

    def __post_init__(self) -> None:
        if self.expected_range is not None:
            low, high = self.expected_range
            if low <= 0 or high <= 0:
                raise ValueError(
                    f"expected_range 값은 양의 정수여야 한다: {self.expected_range}"
                )
            if low > high:
                raise ValueError(
                    f"expected_range 하한이 상한보다 크다: {self.expected_range}"
                )
        if self.missing_draws and self.is_continuous:
            raise ValueError(
                "missing_draws 가 있는데 is_continuous=True — 연속성 판정이 어긋난다"
            )
        # 오름차순/중복 없음 불변식을 조기 검증한다(호출자가 정렬 순서를 가정할 수 있도록).
        if list(self.missing_draws) != sorted(set(self.missing_draws)):
            raise ValueError(
                f"missing_draws 는 오름차순이고 중복이 없어야 한다: {self.missing_draws}"
            )


__all__ = [
    "CacheAction",
    "CacheConfig",
    "CacheGapReport",
    "CacheReadyResult",
    "CacheStatus",
    "RefreshPolicy",
    "StaleReason",
]
