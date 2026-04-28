"""외부 동행복권 응답 JSON 을 도메인 타입으로 변환한다.

원본 응답 키 예시:
    {
        "returnValue": "success",
        "drwNo": 1120,
        "drwNoDate": "2024-06-01",
        "drwtNo1": 1, "drwtNo2": 2, ... "drwtNo6": 6,
        "bnusNo": 7,
        "totSellamnt": 1234567890,
        "firstWinamnt": 1000000000
    }

본 모듈은 네트워크/저장 부수 작용을 갖지 않는 순수 함수만 노출한다.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .models import DrawNotFoundError, LottoDraw

_NUMBER_KEYS = ("drwtNo1", "drwtNo2", "drwtNo3", "drwtNo4", "drwtNo5", "drwtNo6")


def parse_draw(payload: dict[str, Any]) -> LottoDraw:
    """동행복권 회차 응답을 :class:`LottoDraw` 로 변환한다.

    실패 정책:
    - ``returnValue`` 가 ``"success"`` 가 아니면 :class:`DrawNotFoundError`.
    - 필수 키 누락이나 타입 불일치는 :class:`ValueError`.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"payload 는 dict 이어야 한다: {type(payload).__name__}")

    return_value = payload.get("returnValue")
    if return_value != "success":
        raise DrawNotFoundError(
            f"동행복권 응답이 success 가 아니다: returnValue={return_value!r}"
        )

    try:
        drw_no = int(payload["drwNo"])
        drw_date = date.fromisoformat(str(payload["drwNoDate"]))
        numbers_raw = tuple(int(payload[k]) for k in _NUMBER_KEYS)
        bonus_no = int(payload["bnusNo"])
    except KeyError as exc:
        raise ValueError(f"필수 키 누락: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        # ValueError 재포장은 메시지 일관성 확보용이다.
        raise ValueError(f"필드 변환 실패: {exc}") from exc

    # 정렬을 여기서 강제한다. 외부 응답 순서에 의존하지 않기 위함이다.
    numbers_sorted = tuple(sorted(numbers_raw))
    if len(numbers_sorted) != 6:
        raise ValueError(f"본 번호가 6개가 아니다: {numbers_sorted}")
    numbers = (
        numbers_sorted[0],
        numbers_sorted[1],
        numbers_sorted[2],
        numbers_sorted[3],
        numbers_sorted[4],
        numbers_sorted[5],
    )

    tot_sell_amnt = _optional_int(payload.get("totSellamnt"))
    first_win_amnt = _optional_int(payload.get("firstWinamnt"))

    return LottoDraw(
        drw_no=drw_no,
        drw_date=drw_date,
        numbers=numbers,
        bonus_no=bonus_no,
        tot_sell_amnt=tot_sell_amnt,
        first_win_amnt=first_win_amnt,
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        # 외부 응답 포맷이 소수/문자열일 때도 관대하게 처리한다.
        return None


__all__ = ["parse_draw"]
