"""동행복권 회차 단건 조회 HTTP 클라이언트.

재시도, 요청 간 최소 간격, 타임아웃, User-Agent 설정을 담당한다.
스키마 매핑 책임은 본 모듈에 없다. 본 모듈은 ``FetchResult`` 형태로
원본 JSON 을 반환하고, 매핑은 ``serialization.parse_draw`` 에 위임한다.

외부 API 3-티어 fallback: live → cache → seed.
"""

from __future__ import annotations

import json
import logging
import pathlib
import time
from datetime import date, datetime
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover - 런타임 설치 누락 시 가이드 목적
    raise ImportError(
        "동행복권 HTTP 클라이언트는 `requests` 패키지를 필요로 한다. "
        "`pip install requests` 로 설치한다."
    ) from exc

from .models import DrawNotFoundError, FetchResult, LottoDraw, TransientFetchError

# lotto_predictor_v2 프로젝트 루트 기준 seed 파일 경로
# __file__: .../lotto_predictor_v2/src/lotto_predictor/backend/http_client.py
#  .parent x4 → lotto_predictor_v2/
_SEED_FILE = pathlib.Path(__file__).parent.parent.parent.parent / "seed_draws.json"

_LOGGER = logging.getLogger(__name__)

_ENDPOINT = "https://www.dhlottery.co.kr/common.do"
_DEFAULT_USER_AGENT = (
    "lotto-predictor/0.1 (+https://github.com/; contact: local-build)"
)


class DhLotteryClient:
    """동행복권 공식 엔드포인트 회차 단건 조회기."""

    def __init__(
        self,
        *,
        timeout: float = 5.0,
        max_retries: int = 3,
        user_agent: str = _DEFAULT_USER_AGENT,
        min_interval: float = 0.2,
        backoff_base: float = 0.5,
        session: "requests.Session | None" = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError(f"timeout 은 양수여야 한다: {timeout}")
        if max_retries < 0:
            raise ValueError(f"max_retries 는 0 이상이어야 한다: {max_retries}")
        if min_interval < 0:
            raise ValueError(f"min_interval 은 0 이상이어야 한다: {min_interval}")
        if backoff_base <= 0:
            raise ValueError(f"backoff_base 는 양수여야 한다: {backoff_base}")

        self._timeout = timeout
        self._max_retries = max_retries
        self._min_interval = min_interval
        self._backoff_base = backoff_base
        self._last_request_ts: float = 0.0

        self._owns_session = session is None
        self._session = session if session is not None else requests.Session()
        self._session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})

    # ------------------------------------------------------------------
    # 수명 주기
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> "DhLotteryClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    def fetch_draw(self, draw_no: int) -> FetchResult:
        """회차 단건을 조회해 원본 payload 를 포함한 :class:`FetchResult` 반환."""
        if draw_no <= 0:
            raise ValueError(f"draw_no 는 양의 정수여야 한다: {draw_no}")

        params = {"method": "getLottoNumber", "drwNo": int(draw_no)}
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            self._respect_rate_limit()
            try:
                response = self._session.get(
                    _ENDPOINT, params=params, timeout=self._timeout
                )
            except requests.RequestException as exc:
                last_exc = exc
                _LOGGER.warning(
                    "동행복권 요청 실패(네트워크) drw_no=%s attempt=%s error=%s",
                    draw_no,
                    attempt,
                    exc,
                )
                self._sleep_backoff(attempt)
                continue

            if _is_retryable_status(response.status_code):
                last_exc = TransientFetchError(
                    f"HTTP {response.status_code} 응답: drw_no={draw_no}"
                )
                _LOGGER.warning(
                    "동행복권 요청 실패(상태코드) drw_no=%s attempt=%s status=%s",
                    draw_no,
                    attempt,
                    response.status_code,
                )
                self._sleep_backoff(attempt)
                continue

            if response.status_code != 200:
                # 404 등 영구 오류: 재시도 없이 즉시 종료.
                raise DrawNotFoundError(
                    f"동행복권 응답 비정상: status={response.status_code} drw_no={draw_no}"
                )

            try:
                payload: Any = response.json()
            except ValueError as exc:
                raise ValueError(
                    f"동행복권 응답이 JSON 이 아니다: drw_no={draw_no}, error={exc}"
                ) from exc

            if not isinstance(payload, dict):
                raise ValueError(
                    f"동행복권 응답이 dict 가 아니다: drw_no={draw_no}, type={type(payload).__name__}"
                )

            return_value = payload.get("returnValue")
            if return_value != "success":
                raise DrawNotFoundError(
                    f"회차 없음: drw_no={draw_no}, returnValue={return_value!r}"
                )

            return FetchResult(
                draw_no=int(draw_no),
                payload=payload,
                fetched_at=datetime.now(),
            )

        raise TransientFetchError(
            f"재시도 후에도 회차 조회 실패: drw_no={draw_no}, last_error={last_exc!r}"
        )

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _respect_rate_limit(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    def _sleep_backoff(self, attempt: int) -> None:
        # 지수 백오프: backoff_base * 2^attempt.
        delay = self._backoff_base * (2 ** attempt)
        time.sleep(delay)


def _is_retryable_status(status_code: int) -> bool:
    """재시도 대상 HTTP 상태 코드 판정.

    - 408 Request Timeout
    - 429 Too Many Requests
    - 5xx 서버 오류
    """
    if status_code in (408, 429):
        return True
    return 500 <= status_code <= 599


class ThreeTierLotteryClient:
    """동행복권 3-티어 fallback 클라이언트.

    Tier 1 live  : DhLotteryClient (실시간 API)
    Tier 2 cache : SQLite DB (LottoStorage)
    Tier 3 seed  : seed_draws.json (정적 번들 데이터)
    """

    def __init__(
        self,
        live_client: DhLotteryClient | None = None,
        cache_db_path: pathlib.Path | None = None,
    ) -> None:
        self._live = live_client or DhLotteryClient()
        self._cache_db_path = cache_db_path

    def fetch_draw(self, draw_no: int) -> FetchResult:
        """3-티어 순서로 회차 데이터를 조회한다."""
        # Tier 1: live API
        try:
            result = self._live.fetch_draw(draw_no)
            _LOGGER.debug("fetch_draw drw_no=%d source=live", draw_no)
            return result
        except Exception as exc:
            _LOGGER.warning("Tier1 live 실패 drw_no=%d: %s — Tier2 cache 시도", draw_no, exc)

        # Tier 2: SQLite cache
        try:
            cached = self._fetch_from_cache(draw_no)
            if cached is not None:
                _LOGGER.info("fetch_draw drw_no=%d source=cache", draw_no)
                return cached
        except Exception as exc:
            _LOGGER.warning("Tier2 cache 실패 drw_no=%d: %s — Tier3 seed 시도", draw_no, exc)

        # Tier 3: seed file
        seed = self._fetch_from_seed(draw_no)
        if seed is not None:
            _LOGGER.info("fetch_draw drw_no=%d source=seed", draw_no)
            return seed

        raise DrawNotFoundError(f"3-티어 모두 실패: drw_no={draw_no}")

    def fetch_range(self, start: int, end: int) -> list[FetchResult]:
        """start~end 범위 회차를 일괄 조회한다 (3-티어 적용)."""
        results: list[FetchResult] = []
        for drw_no in range(start, end + 1):
            try:
                results.append(self.fetch_draw(drw_no))
            except DrawNotFoundError:
                _LOGGER.warning("drw_no=%d 를 찾을 수 없어 건너뜀", drw_no)
        return results

    def _fetch_from_cache(self, draw_no: int) -> FetchResult | None:
        if self._cache_db_path is None:
            default_path = pathlib.Path.home() / ".lotto_cache" / "draws.db"
            if not default_path.exists():
                return None
            self._cache_db_path = default_path
        try:
            import contextlib
            import sqlite3
            with contextlib.closing(sqlite3.connect(str(self._cache_db_path))) as conn:
                row = conn.execute(
                    "SELECT drw_no, drw_date, n1, n2, n3, n4, n5, n6, bonus_no"
                    " FROM lotto_draw WHERE drw_no = ?",
                    (draw_no,),
                ).fetchone()
            if row is None:
                return None
            payload = {
                "returnValue": "success",
                "drwNo": row[0],
                "drwNoDate": row[1],
                "drwtNo1": row[2], "drwtNo2": row[3], "drwtNo3": row[4],
                "drwtNo4": row[5], "drwtNo5": row[6], "drwtNo6": row[7],
                "bnusNo": row[8],
            }
            return FetchResult(draw_no=draw_no, payload=payload, fetched_at=datetime.now())
        except Exception:
            return None

    def _fetch_from_seed(self, draw_no: int) -> FetchResult | None:
        if not _SEED_FILE.exists():
            return None
        try:
            data = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
            for entry in data.get("draws", []):
                if entry.get("drw_no") == draw_no:
                    nums = entry["numbers"]
                    payload = {
                        "returnValue": "success",
                        "drwNo": draw_no,
                        "drwNoDate": entry.get("drw_date", ""),
                        "drwtNo1": nums[0], "drwtNo2": nums[1], "drwtNo3": nums[2],
                        "drwtNo4": nums[3], "drwtNo5": nums[4], "drwtNo6": nums[5],
                        "bnusNo": entry.get("bonus_no", 0),
                    }
                    return FetchResult(draw_no=draw_no, payload=payload, fetched_at=datetime.now())
        except Exception as exc:
            _LOGGER.warning("seed 파일 파싱 실패: %s", exc)
        return None

    def load_seed_draws(self) -> list[LottoDraw]:
        """seed_draws.json 전체를 LottoDraw 목록으로 반환한다."""
        if not _SEED_FILE.exists():
            return []
        try:
            data = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
            result: list[LottoDraw] = []
            for entry in data.get("draws", []):
                nums = entry["numbers"]
                drw_date_str = entry.get("drw_date", "2000-01-01")
                drw_date = date.fromisoformat(drw_date_str)
                result.append(LottoDraw(
                    drw_no=entry["drw_no"],
                    drw_date=drw_date,
                    numbers=tuple(nums[:6]),  # type: ignore[arg-type]
                    bonus_no=entry.get("bonus_no", 0),
                ))
            return result
        except Exception as exc:
            _LOGGER.warning("seed draws 로드 실패: %s", exc)
            return []


__all__ = ["DhLotteryClient", "ThreeTierLotteryClient"]
