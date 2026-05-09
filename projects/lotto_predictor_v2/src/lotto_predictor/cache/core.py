"""회차 데이터 로컬 캐시 저장소 구현.

`LottoDrawCache` 는 Backend Dev `LottoStorage`(저수준 CRUD) 와 Frontend Dev
`LottoCollector`(증분 수집) 위에 얹는 **캐시 정책 계층** 이다. SQL 을 직접
발행하지 않고 저장소 공개 메서드만 사용하며, HTTP 호출은 수집기에 위임한다.

본 모듈이 담당하는 네 가지 책임:
1. 도메인 수준 신선도 판정(`status`).
2. 필요 시 수집 위임 호출과 결과 요약(`ensure_ready`).
3. 도메인 읽기 API 노출(`get_recent_draws`, `get_all_draws`, `get_draw`).
4. 연속 회차 범위 검증(`validate_continuity`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Callable, Protocol, runtime_checkable

from lotto_predictor.backend import FetchCheckpoint, LottoDraw, LottoStorage
from lotto_predictor.collector import LottoCollector, SyncResult

from .models import (
    CacheAction,
    CacheConfig,
    CacheGapReport,
    CacheReadyResult,
    CacheStatus,
    StaleReason,
)

_DEFAULT_LOGGER = logging.getLogger("lotto_predictor.cache")


@runtime_checkable
class _CollectorLike(Protocol):
    """수집기 위임 호출에 필요한 최소 인터페이스.

    `LottoCollector` 가 본 Protocol 을 충족하며, 테스트는 동일 시그니처의 fake
    로 대체할 수 있다.
    """

    def sync_incremental(self) -> SyncResult: ...


class LottoDrawCache:
    """회차 데이터 로컬 캐시의 정책 계층.

    의존성 주입:
    - ``storage``: Backend Dev `LottoStorage`. 본 클래스는 연결 수명을 관리하지 않는다.
    - ``collector``: Frontend Dev `LottoCollector`. 미주입이면 수집 호출이 생략된다.
    - ``config``: 신선도/정책 설정.
    - ``clock``: 현재 시각 함수. 테스트에서 고정 시간을 주입할 수 있다.
    - ``logger``: 주입된 로거. 없으면 기본 `lotto_predictor.cache` 사용.
    """

    def __init__(
        self,
        storage: LottoStorage,
        collector: _CollectorLike | None = None,
        config: CacheConfig | None = None,
        clock: Callable[[], datetime] = datetime.now,
        logger: logging.Logger | None = None,
    ) -> None:
        self._storage = storage
        self._collector = collector
        self._config = config if config is not None else CacheConfig()
        self._clock = clock
        self._logger = logger if logger is not None else _DEFAULT_LOGGER

    # ------------------------------------------------------------------
    # 공개 API: 상태 요약
    # ------------------------------------------------------------------
    def status(self) -> CacheStatus:
        """현재 캐시 상태를 계산한다.

        - 회차 개수는 저장소 내 모든 회차를 조회해 집계한다(한 번의 호출로 완료).
        - 체크포인트가 없으면 `missing_checkpoint` 를 사유로 기록한다.
        - 체크포인트가 있어도 회차 개수가 `required_draws` 미만이면
          `insufficient_draws` 를 추가한다.
        - 체크포인트의 ``fetched_at`` 이 ``freshness_hours`` 이상 경과했으면
          `expired_checkpoint` 를 추가한다.
        """
        checkpoint = self._storage.get_checkpoint()
        draws = self._storage.get_draws()
        return self._compute_status(checkpoint=checkpoint, draws=draws)

    # ------------------------------------------------------------------
    # 공개 API: 준비 플로우
    # ------------------------------------------------------------------
    def ensure_ready(self) -> CacheReadyResult:
        """필요 시 수집을 위임 호출하고 최종 상태를 반환한다.

        실행 경로:
        - `offline=True` 또는 `refresh_policy="never"` 또는 `collector` 미주입
          → 수집을 생략하고 현재 상태를 그대로 반환한다.
          (collector 미주입이거나 offline 이면 ``action="offline"``,
          refresh_policy="never" 이면 ``action="skipped"``.)
        - 위 조건이 아니어도 현재 상태가 신선하면(``is_stale=False``)
          ``action="skipped"`` 로 즉시 반환한다.
        - 신선하지 않으면 `collector.sync_incremental()` 을 호출하고, 이후 갱신된
          상태를 재계산해 ``action="synced"`` 로 반환한다. 수집 결과는 예외로
          올리지 않고 ``sync_result`` 에 보존한다.
        """
        current = self.status()

        if self._config.offline or self._collector is None:
            self._logger.debug(
                "ensure_ready: offline/collector 미주입 — 수집 생략 (is_stale=%s)",
                current.is_stale,
            )
            return CacheReadyResult(status=current, action="offline")

        if self._config.refresh_policy == "never":
            self._logger.debug(
                "ensure_ready: refresh_policy='never' — 수집 생략 (is_stale=%s)",
                current.is_stale,
            )
            return CacheReadyResult(status=current, action="skipped")

        if not current.is_stale:
            self._logger.debug("ensure_ready: 캐시 신선 — 수집 생략")
            return CacheReadyResult(status=current, action="skipped")

        self._logger.info(
            "ensure_ready: 캐시 오래됨(reasons=%s) — 수집 위임 호출",
            list(current.stale_reasons),
        )
        sync_result = self._collector.sync_incremental()
        refreshed = self.status()
        return CacheReadyResult(
            status=refreshed,
            action="synced",
            sync_result=sync_result,
        )

    # ------------------------------------------------------------------
    # 공개 API: 읽기
    # ------------------------------------------------------------------
    def get_recent_draws(self, n: int) -> list[LottoDraw]:
        """최신 ``n`` 개 회차를 내림차순으로 반환한다.

        Backend Dev `LottoStorage.get_draws(limit=n)` 계약(내림차순)을 그대로
        재사용해 상위 소비자가 최근 회차를 빠르게 참조할 수 있게 한다.
        """
        if n <= 0:
            raise ValueError(f"n 은 양의 정수여야 한다: {n}")
        return self._storage.get_draws(limit=n)

    def get_all_draws(self) -> list[LottoDraw]:
        """저장된 전체 회차를 오름차순으로 반환한다.

        저장소 반환 순서(내림차순)를 통계 집계가 기대하는 오름차순으로 뒤집는다.
        원본 리스트를 수정하지 않기 위해 ``reversed`` 로 새 리스트를 만든다.
        """
        draws = self._storage.get_draws()
        return list(reversed(draws))

    def get_draw(self, draw_no: int) -> LottoDraw | None:
        """단일 회차를 반환한다. 존재하지 않으면 ``None``."""
        if draw_no <= 0:
            raise ValueError(f"draw_no 는 양의 정수여야 한다: {draw_no}")
        return self._storage.get_draw(draw_no)

    # ------------------------------------------------------------------
    # 공개 API: 연속성 검증
    # ------------------------------------------------------------------
    def validate_continuity(self) -> CacheGapReport:
        """저장된 회차 범위 내 누락 회차를 보고한다.

        - 저장소가 비어 있으면 ``expected_range=None``, ``is_continuous=True``.
        - 그렇지 않으면 `[earliest..latest]` 전체 구간을 기대 범위로 하고,
          저장된 회차 집합과 비교해 누락된 번호를 오름차순으로 나열한다.
        """
        draws = self._storage.get_draws()
        if not draws:
            return CacheGapReport(expected_range=None)

        stored = {d.drw_no for d in draws}
        earliest = min(stored)
        latest = max(stored)
        missing = tuple(no for no in range(earliest, latest + 1) if no not in stored)
        return CacheGapReport(
            expected_range=(earliest, latest),
            missing_draws=missing,
            is_continuous=not missing,
        )

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _compute_status(
        self,
        *,
        checkpoint: FetchCheckpoint | None,
        draws: list[LottoDraw],
    ) -> CacheStatus:
        """체크포인트와 저장된 회차로부터 `CacheStatus` 를 조립한다."""
        total = len(draws)
        latest_no: int | None = None
        earliest_no: int | None = None
        if draws:
            # 저장소가 내림차순을 보장하므로 양 끝을 그대로 사용한다.
            latest_no = draws[0].drw_no
            earliest_no = draws[-1].drw_no

        reasons: list[StaleReason] = []
        if checkpoint is None:
            reasons.append("missing_checkpoint")
        if total < self._config.required_draws:
            reasons.append("insufficient_draws")
        if checkpoint is not None and self._is_checkpoint_expired(checkpoint):
            reasons.append("expired_checkpoint")

        is_stale = bool(reasons)
        return CacheStatus(
            total_draws=total,
            latest_drw_no=latest_no,
            earliest_drw_no=earliest_no,
            last_fetched_at=checkpoint.fetched_at if checkpoint is not None else None,
            is_stale=is_stale,
            stale_reasons=tuple(reasons),
        )

    def _is_checkpoint_expired(self, checkpoint: FetchCheckpoint) -> bool:
        """체크포인트가 `freshness_hours` 이상 경과했으면 True."""
        if self._config.freshness_hours <= 0:
            # 0 이면 "항상 만료"가 아니라 "만료 판정을 하지 않음"으로 해석한다.
            return False
        try:
            now = self._clock()
        except Exception:  # pylint: disable=broad-except
            self._logger.exception("clock 호출 실패 — 체크포인트 만료 판정을 건너뛴다")
            return False
        elapsed = now - checkpoint.fetched_at
        return elapsed >= timedelta(hours=self._config.freshness_hours)


__all__ = ["LottoDrawCache"]
