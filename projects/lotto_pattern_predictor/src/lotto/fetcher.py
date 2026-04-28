"""동행복권 API 데이터 수집 모듈.

동행복권(dhlottery.co.kr) 공개 API에서 로또 당첨번호를 회차별로 수집한다.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Callable

import requests

from .exceptions import DrawNotFoundError, FetchError
from .models import DrawResult

logger = logging.getLogger(__name__)

# 동행복권 공개 API 엔드포인트
_API_URL = "https://www.dhlottery.co.kr/common.do"
_DEFAULT_TIMEOUT = 10  # 초
_DEFAULT_DELAY = 0.5  # 요청 간 대기 (초) — API 차단 방지
_MAX_RETRIES = 3


def _parse_draw_response(data: dict) -> DrawResult:
    """API JSON 응답을 DrawResult로 변환한다.

    동행복권 API 응답 필드:
        returnValue, drwNo, drwNoDate,
        drwtNo1~drwtNo6, bnusNo,
        totSellamnt, firstWinamnt, firstPrzwnerCo
    """
    if data.get("returnValue") != "success":
        draw_no = data.get("drwNo", 0)
        raise DrawNotFoundError(int(draw_no) if draw_no else 0)

    try:
        numbers = tuple(sorted(data[f"drwtNo{i}"] for i in range(1, 7)))
        draw_date = datetime.strptime(data["drwNoDate"], "%Y-%m-%d").date()

        return DrawResult(
            draw_no=int(data["drwNo"]),
            draw_date=draw_date,
            numbers=numbers,
            bonus=int(data["bnusNo"]),
            total_sell_amount=int(data.get("totSellamnt", 0)),
            first_prize_amount=int(data.get("firstWinamnt", 0)),
            first_prize_winners=int(data.get("firstPrzwnerCo", 0)),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise FetchError(f"API 응답 파싱 실패: {e}") from e


class LottoFetcher:
    """동행복권 API에서 로또 당첨번호를 수집하는 클래스.

    사용 예:
        fetcher = LottoFetcher()
        result = fetcher.fetch_draw(1100)
        results = fetcher.fetch_range(1001, 1100)
    """

    def __init__(
        self,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        delay: float = _DEFAULT_DELAY,
        max_retries: int = _MAX_RETRIES,
        session: requests.Session | None = None,
    ) -> None:
        self._timeout = timeout
        self._delay = delay
        self._max_retries = max_retries
        self._session = session or self._create_session()

    @staticmethod
    def _create_session() -> requests.Session:
        """기본 헤더가 설정된 requests 세션을 생성한다."""
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        return s

    def fetch_draw(self, draw_no: int) -> DrawResult:
        """단일 회차 당첨번호를 가져온다.

        Args:
            draw_no: 회차 번호 (1 이상)

        Returns:
            DrawResult 객체

        Raises:
            DrawNotFoundError: 해당 회차가 존재하지 않을 때
            FetchError: 네트워크 오류 또는 파싱 실패 시
        """
        if draw_no < 1:
            raise ValueError(f"회차 번호는 1 이상이어야 합니다: {draw_no}")

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._session.get(
                    _API_URL,
                    params={"method": "getLottoNumber", "drwNo": draw_no},
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return _parse_draw_response(data)
            except DrawNotFoundError:
                raise
            except requests.RequestException as e:
                last_error = FetchError(
                    f"회차 {draw_no} 수집 실패 (시도 {attempt}/{self._max_retries}): {e}"
                )
                logger.warning(str(last_error))
                if attempt < self._max_retries:
                    time.sleep(self._delay * attempt)
            except FetchError:
                raise

        raise last_error  # type: ignore[misc]

    def fetch_range(
        self,
        start: int,
        end: int,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[DrawResult]:
        """연속 회차 범위의 당첨번호를 수집한다.

        Args:
            start: 시작 회차 (포함)
            end: 종료 회차 (포함)
            on_progress: 진행 콜백 (현재 회차, 전체 수)

        Returns:
            DrawResult 리스트 (회차 오름차순)

        Raises:
            FetchError: 수집 중 복구 불가능한 오류 발생 시
        """
        if start > end:
            raise ValueError(f"시작 회차({start})가 종료 회차({end})보다 큽니다")

        results: list[DrawResult] = []
        total = end - start + 1

        for i, draw_no in enumerate(range(start, end + 1), 1):
            try:
                result = self.fetch_draw(draw_no)
                results.append(result)
                logger.debug("회차 %d 수집 완료 (%d/%d)", draw_no, i, total)
            except DrawNotFoundError:
                # 미래 회차이거나 누락된 회차 — 건너뛴다
                logger.info("회차 %d 데이터 없음, 건너뜀", draw_no)
                continue

            if on_progress:
                on_progress(i, total)

            # API 차단 방지를 위한 요청 간 대기
            if i < total:
                time.sleep(self._delay)

        return results

    def fetch_latest(self) -> DrawResult:
        """가장 최근 회차의 당첨번호를 가져온다.

        최신 회차를 탐색하기 위해 충분히 큰 회차 번호로 시작하여
        이진 탐색으로 마지막 유효 회차를 찾는다.

        Returns:
            가장 최근 DrawResult

        Raises:
            FetchError: 수집 실패 시
        """
        # 이진 탐색으로 최신 회차 탐색
        low, high = 1, 2000  # 충분히 큰 상한

        # 상한 조정: high가 유효하면 상한을 올린다
        while True:
            try:
                self.fetch_draw(high)
                high *= 2
            except DrawNotFoundError:
                break
            except FetchError:
                break

        # 이진 탐색
        latest: DrawResult | None = None
        while low <= high:
            mid = (low + high) // 2
            try:
                result = self.fetch_draw(mid)
                latest = result
                low = mid + 1
            except DrawNotFoundError:
                high = mid - 1
            time.sleep(self._delay)

        if latest is None:
            raise FetchError("최신 회차를 찾을 수 없습니다")

        return latest

    def fetch_recent(
        self,
        count: int = 500,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[DrawResult]:
        """최근 N회차의 당첨번호를 수집한다.

        Args:
            count: 수집할 회차 수 (기본 500)
            on_progress: 진행 콜백

        Returns:
            DrawResult 리스트 (회차 오름차순)
        """
        latest = self.fetch_latest()
        start = max(1, latest.draw_no - count + 1)
        return self.fetch_range(start, latest.draw_no, on_progress=on_progress)

    def close(self) -> None:
        """HTTP 세션을 닫는다."""
        self._session.close()

    def __enter__(self) -> LottoFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
