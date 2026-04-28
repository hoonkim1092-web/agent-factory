"""동행복권 회차 수집 오케스트레이션 구현.

Backend Dev 계층의 ``DhLotteryClient`` 와 ``LottoStorage`` 위에 얹혀
증분 수집 루프, 최신 회차 탐색, 명시 범위 수집을 담당한다. 저수준 HTTP/
SQLite 부수효과는 Backend Dev 계층에 위임하고, 본 모듈은 루프/체크포인트/
부분 성공 집계 책임만 진다.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Protocol, runtime_checkable

from lotto_predictor.backend import (
    DrawNotFoundError,
    FetchCheckpoint,
    FetchResult,
    LottoDraw,
    LottoStorage,
    TransientFetchError,
    parse_draw,
)

from .models import CollectorConfig, FetchFailure, SyncResult

_DEFAULT_LOGGER = logging.getLogger("lotto_predictor.collector")

# 동행복권 체크포인트 소스 식별자. 증분 수집이 어떤 외부 출처에서 왔는지를
# ``FetchCheckpoint.source_url`` 에 기록해 둔다.
_SOURCE_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber"


@runtime_checkable
class DrawFetcher(Protocol):
    """수집기가 의존하는 회차 단건 조회 인터페이스.

    Backend Dev ``DhLotteryClient`` 가 이 Protocol 을 충족하며, 테스트는
    동일 시그니처를 갖는 경량 fake 로 대체할 수 있다.
    """

    def fetch_draw(self, draw_no: int) -> FetchResult: ...


class LottoCollector:
    """동행복권 회차 증분 수집기.

    의존성 주입 포인트:
    - ``client``: 단일 회차 조회. HTTP 재시도·타임아웃은 클라이언트가 책임진다.
    - ``storage``: 회차/체크포인트 영속 계층. 연결 수명은 호출자가 관리한다.
    - ``config``: 루프 제어 설정.
    - ``logger``: 주입된 로거. 없으면 기본 ``lotto_predictor.collector`` 사용.
    """

    def __init__(
        self,
        client: DrawFetcher,
        storage: LottoStorage,
        config: CollectorConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self._config = config if config is not None else CollectorConfig()
        self._logger = logger if logger is not None else _DEFAULT_LOGGER
        # 외부 호출 시각(단조시계). ``min_interval_s`` 간격 보장에 사용된다.
        self._last_call_ts: float = 0.0

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def detect_latest_draw_no(self, probe_start: int) -> int:
        """``probe_start`` 에서 전진하며 마지막 발표 회차 번호를 반환한다.

        전략:
        - ``probe_start`` 번째 회차를 먼저 확인한다. 해당 회차가 존재하지 않으면
          상위 구간은 더 볼 필요가 없으므로 ``probe_start - 1`` 을 반환한다.
        - 존재한다면 ``probe_start + 1`` 부터 ``DrawNotFoundError`` 가 나올
          때까지 최대 ``config.max_probe`` 번 전진한다.
        - 프로브 횟수 한계를 넘으면 직전까지 성공한 회차를 반환한다.
        """
        if probe_start <= 0:
            raise ValueError(f"probe_start 는 양의 정수여야 한다: {probe_start}")

        latest_confirmed: int | None = None
        draw_no = probe_start
        probed = 0
        while probed < self._config.max_probe:
            outcome = self._fetch_one(draw_no)
            probed += 1
            if outcome.draw is not None:
                latest_confirmed = outcome.draw.drw_no
                draw_no += 1
                continue

            # 첫 번째 프로브가 곧바로 실패한 경우에만 이전 회차로 되돌린다.
            if outcome.reason == "not_yet_drawn":
                if latest_confirmed is None:
                    # 기준 회차 자체가 미발표라면 직전 회차를 추정 결과로 반환.
                    return max(probe_start - 1, 0)
                return latest_confirmed

            # 일시 실패는 최신 회차 탐색에서는 결정적 답을 얻을 수 없으므로 전파.
            raise TransientFetchError(
                f"최신 회차 탐색 중 일시 실패: drw_no={draw_no}, detail={outcome.detail}"
            )

        # max_probe 도달: 지금까지 확인된 값을 돌려준다.
        if latest_confirmed is None:
            # 첫 회 확인조차 못 한 상황(매우 드묾). 호출자가 재시도하도록 전파.
            raise TransientFetchError(
                f"max_probe({self._config.max_probe}) 내에 최신 회차를 확정하지 못했다"
            )
        return latest_confirmed

    def sync_range(self, start: int, end: int) -> SyncResult:
        """``start`` ~ ``end`` 회차를 순차 수집한다(포함 양끝).

        - 성공 회차는 ``upsert_draws`` 로 즉시 저장한다.
        - 미발표(``not_yet_drawn``)는 ``FetchFailure`` 로 기록하고 루프를 이어간다.
        - 일시 실패가 ``abort_on_consecutive_failures`` 이상 연속되면 즉시 중단.
        - 범위 마지막까지 도달하면 ``stopped_reason="caught_up"``.
        """
        if start <= 0 or end <= 0:
            raise ValueError(f"범위는 양의 정수여야 한다: start={start}, end={end}")
        if start > end:
            raise ValueError(f"start > end: start={start}, end={end}")

        fetched: list[LottoDraw] = []
        failures: list[FetchFailure] = []
        consecutive_transient = 0
        last_success: int | None = None
        stopped_reason = "caught_up"

        for draw_no in range(start, end + 1):
            outcome = self._fetch_one(draw_no)
            if outcome.draw is not None:
                self._persist_draw(outcome.draw)
                fetched.append(outcome.draw)
                last_success = outcome.draw.drw_no
                consecutive_transient = 0
                continue

            failures.append(
                FetchFailure(
                    draw_no=draw_no,
                    reason=outcome.reason,
                    detail=outcome.detail,
                )
            )
            if outcome.reason == "transient" or outcome.reason == "rate_limited":
                consecutive_transient += 1
                if consecutive_transient >= self._config.abort_on_consecutive_failures:
                    stopped_reason = "aborted"
                    break
            else:
                # 일시 실패가 아닌 사유(not_yet_drawn, unknown)는 연속 카운터 초기화.
                consecutive_transient = 0

        if last_success is not None:
            self._update_checkpoint(last_success)

        return SyncResult(
            fetched=fetched,
            failures=failures,
            last_fetched_drw_no=last_success,
            stopped_reason=stopped_reason,
        )

    def sync_incremental(self) -> SyncResult:
        """저장소 체크포인트에서 시작해 최신 회차까지 증분 수집한다.

        - 체크포인트가 없으면 1번 회차부터 시작한다.
        - ``config.target_draw_no`` 가 주어지면 해당 회차까지만 수집한다.
        - 타겟이 없으면 ``detect_latest_draw_no`` 로 상한을 추정한다.
        - 최신 회차에 도달했거나 미발표 회차를 만나면 각각 ``caught_up`` /
          ``not_yet_drawn`` 로 종료한다.
        """
        checkpoint = self._storage.get_checkpoint()
        start = (checkpoint.last_fetched_drw_no + 1) if checkpoint is not None else 1

        target = self._config.target_draw_no
        if target is None:
            probe_start = start if checkpoint is None else checkpoint.last_fetched_drw_no + 1
            try:
                target = self.detect_latest_draw_no(probe_start)
            except TransientFetchError as exc:
                # 최신 회차 탐색 단계에서 일시 실패 시 실패로 기록하고 중단.
                self._logger.warning("최신 회차 탐색 일시 실패: %s", exc)
                return SyncResult(
                    fetched=[],
                    failures=[
                        FetchFailure(
                            draw_no=probe_start,
                            reason="transient",
                            detail=str(exc),
                        )
                    ],
                    last_fetched_drw_no=(
                        checkpoint.last_fetched_drw_no if checkpoint is not None else None
                    ),
                    stopped_reason="aborted",
                )

        if start > target:
            # 이미 최신 상태이면 체크포인트는 그대로 두고 빈 결과 반환.
            return SyncResult(
                fetched=[],
                failures=[],
                last_fetched_drw_no=(
                    checkpoint.last_fetched_drw_no if checkpoint is not None else None
                ),
                stopped_reason="caught_up",
            )

        fetched: list[LottoDraw] = []
        failures: list[FetchFailure] = []
        consecutive_transient = 0
        last_success: int | None = (
            checkpoint.last_fetched_drw_no if checkpoint is not None else None
        )
        stopped_reason: str = "caught_up"

        draw_no = start
        while draw_no <= target:
            outcome = self._fetch_one(draw_no)
            if outcome.draw is not None:
                self._persist_draw(outcome.draw)
                fetched.append(outcome.draw)
                last_success = outcome.draw.drw_no
                consecutive_transient = 0
                draw_no += 1
                continue

            if outcome.reason == "not_yet_drawn":
                # 타겟 이전에 미발표 회차를 만났다면 최신화가 막힌 것이므로 종료.
                stopped_reason = "not_yet_drawn"
                break

            failures.append(
                FetchFailure(
                    draw_no=draw_no,
                    reason=outcome.reason,
                    detail=outcome.detail,
                )
            )
            if outcome.reason in ("transient", "rate_limited"):
                consecutive_transient += 1
                if consecutive_transient >= self._config.abort_on_consecutive_failures:
                    stopped_reason = "aborted"
                    break
                # 같은 회차를 재시도하지 않고 다음 회차로 전진: 연속 실패 판단을 위해.
                draw_no += 1
            else:
                consecutive_transient = 0
                draw_no += 1

        if stopped_reason == "caught_up" and self._config.target_draw_no is not None:
            # 명시 타겟이 지정된 경우는 종료 사유를 구분해 노출한다.
            stopped_reason = "target_reached"

        if last_success is not None and (
            checkpoint is None or last_success > checkpoint.last_fetched_drw_no
        ):
            self._update_checkpoint(last_success)

        return SyncResult(
            fetched=fetched,
            failures=failures,
            last_fetched_drw_no=last_success,
            stopped_reason=stopped_reason,  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _fetch_one(self, draw_no: int) -> "_FetchOutcome":
        """단일 회차 조회를 수집기 관점의 결과 객체로 정규화한다."""
        self._sleep_between_calls()
        try:
            result = self._client.fetch_draw(draw_no)
        except DrawNotFoundError as exc:
            self._logger.info("회차 미발표/없음 감지: drw_no=%s detail=%s", draw_no, exc)
            return _FetchOutcome(draw=None, reason="not_yet_drawn", detail=str(exc))
        except TransientFetchError as exc:
            self._logger.warning("일시 수집 실패: drw_no=%s detail=%s", draw_no, exc)
            return _FetchOutcome(draw=None, reason="transient", detail=str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.exception("알 수 없는 수집 오류: drw_no=%s", draw_no)
            return _FetchOutcome(draw=None, reason="unknown", detail=repr(exc))

        try:
            draw = parse_draw(result.payload)
        except DrawNotFoundError as exc:
            # 클라이언트가 success 로 내려줬더라도 payload 가 모호하면 미발표로 간주.
            return _FetchOutcome(draw=None, reason="not_yet_drawn", detail=str(exc))
        except ValueError as exc:
            # 스키마 불일치는 구조적 문제이지만 루프를 중단시키지 않고 기록한다.
            self._logger.error("payload 파싱 실패: drw_no=%s error=%s", draw_no, exc)
            return _FetchOutcome(draw=None, reason="unknown", detail=str(exc))

        # 혹시 수집기 호출값과 payload 회차가 다르면 정합성 위반을 상위에 알린다.
        if draw.drw_no != draw_no:
            self._logger.warning(
                "회차 번호 불일치: 요청=%s 응답=%s — 응답 기준으로 저장",
                draw_no,
                draw.drw_no,
            )
        return _FetchOutcome(draw=draw, reason="unknown", detail="")

    def _persist_draw(self, draw: LottoDraw) -> None:
        """성공 회차를 저장소에 위임 저장한다."""
        self._storage.upsert_draws([draw])

    def _update_checkpoint(self, last_success: int) -> None:
        """체크포인트를 최신 성공 회차로 갱신한다."""
        cp = FetchCheckpoint(
            last_fetched_drw_no=last_success,
            fetched_at=datetime.now(),
            source_url=_SOURCE_URL,
        )
        self._storage.set_checkpoint(cp)

    def _sleep_between_calls(self) -> None:
        """외부 호출 간 최소 간격(`min_interval_s`) 을 단조시계 기준으로 보장."""
        interval = self._config.min_interval_s
        if interval <= 0:
            self._last_call_ts = time.monotonic()
            return
        now = time.monotonic()
        remaining = interval - (now - self._last_call_ts)
        if remaining > 0:
            time.sleep(remaining)
        self._last_call_ts = time.monotonic()


class _FetchOutcome:
    """내부 표현: 한 회차 조회의 정규화된 결과.

    - 성공이면 ``draw`` 가 채워지고 ``reason``/``detail`` 은 의미 없음.
    - 실패면 ``draw`` 는 None 이고 ``reason``/``detail`` 을 참고한다.
    """

    __slots__ = ("draw", "reason", "detail")

    def __init__(self, *, draw: LottoDraw | None, reason: str, detail: str) -> None:
        self.draw = draw
        self.reason = reason
        self.detail = detail


__all__ = ["LottoCollector", "DrawFetcher"]
