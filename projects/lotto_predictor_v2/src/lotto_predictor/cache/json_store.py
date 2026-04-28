"""회차 데이터 로컬 JSON 캐시 저장소 구현.

`JsonDrawCacheStore` 는 로컬 JSON 파일(`draws.json`)을 캐시 매체로 사용해
회차별 hit/miss, 만료 판정, 무효화, 파일 락 기반 동시성 제어를 제공한다.
`core.py` 의 `LottoDrawCache` 가 SQLite 저장소 위에 얹는 정책 계층이라면,
본 모듈은 JSON 파일 단독으로 캐시를 관리하는 경량 구현이다.

저장 경로 기본값은 ``~/.lotto_cache/draws.json`` 이며, `fcntl.flock` 기반
파일 락으로 동일 파일을 동시에 쓰는 프로세스/인스턴스를 상호 배제한다.
"""

from __future__ import annotations

import errno
import fcntl
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import StaleReason

_DEFAULT_LOGGER = logging.getLogger("lotto_predictor.cache.json_store")

# 기본 캐시 파일 경로. 상위 소비자가 별도 경로를 지정하지 않으면 본 위치를 사용한다.
DEFAULT_CACHE_DIR = Path.home() / ".lotto_cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "draws.json"


class CacheLockTimeoutError(Exception):
    """파일 락 획득이 지정 시간 내에 실패했을 때 발생하는 예외.

    메시지에는 "파일 락" 이라는 문구와 대상 락 파일 경로, 타임아웃을 포함한다.
    """


@dataclass(frozen=True)
class DrawLookupResult:
    """`JsonDrawCacheStore.get(draw_no)` 결과 묶음.

    - ``hit`` 은 캐시에 해당 회차 원본이 존재하면 ``True``.
    - ``draw`` 는 hit 일 때 원본 JSON dict 의 사본, miss 일 때 ``None``.
    """

    hit: bool
    draw: dict[str, Any] | None


@dataclass(frozen=True)
class JsonCacheStatus:
    """JSON 캐시 현재 상태 요약.

    - ``total_draws`` : 저장된 회차 개수.
    - ``latest_drw_no`` / ``earliest_drw_no`` : 저장된 회차 범위.
    - ``last_fetched_at`` : 메타데이터에 기록된 마지막 수집 시각.
    - ``is_stale`` : `stale_reasons` 가 하나라도 있으면 ``True``.
    - ``stale_reasons`` : 신선도 판정 사유 집합.
    """

    total_draws: int
    latest_drw_no: int | None
    earliest_drw_no: int | None
    last_fetched_at: datetime | None
    is_stale: bool
    stale_reasons: tuple[StaleReason, ...] = ()


class JsonDrawCacheStore:
    """JSON 파일 기반 회차 로컬 캐시 저장소.

    JSON 파일 스키마::

        {
          "metadata": {
            "version": 1,
            "generated_at": "ISO-8601",
            "last_fetched_at": "ISO-8601",
            "freshness_hours": 24,     # optional, 기본 24
            "expires_at": "ISO-8601"   # optional, 있으면 우선 적용
          },
          "draws": [
            {"drwNo": int, "drwNoDate": "...", "numbers": [...], "bnusNo": int}
          ]
        }

    의존성 주입:
    - ``cache_file`` : 캐시 JSON 파일 경로. 존재하지 않으면 빈 스키마로 초기화한다.
    - ``required_draws`` : 최소 보유 회차 수. 부족하면 ``insufficient_draws`` 사유가 붙는다.
    - ``default_freshness_hours`` : 메타데이터에 freshness_hours 가 없을 때 사용할 기본값.
    - ``logger`` : 주입 로거. 미주입 시 ``lotto_predictor.cache.json_store``.
    """

    _DEFAULT_FRESHNESS_HOURS = 24.0
    _LOCK_POLL_INTERVAL = 0.01

    def __init__(
        self,
        cache_file: Path,
        *,
        required_draws: int = 1,
        default_freshness_hours: float = _DEFAULT_FRESHNESS_HOURS,
        logger: logging.Logger | None = None,
    ) -> None:
        if required_draws <= 0:
            raise ValueError(f"required_draws 는 양의 정수여야 한다: {required_draws}")
        if default_freshness_hours < 0:
            raise ValueError(
                f"default_freshness_hours 는 0 이상이어야 한다: {default_freshness_hours}"
            )
        self._cache_file = Path(cache_file)
        self._lock_file = self._cache_file.parent / (self._cache_file.name + ".lock")
        self._required_draws = required_draws
        self._default_freshness_hours = default_freshness_hours
        self._logger = logger or _DEFAULT_LOGGER

    # ------------------------------------------------------------------
    # 팩토리
    # ------------------------------------------------------------------
    @classmethod
    def from_json(
        cls,
        cache_file: str | os.PathLike[str] | None = None,
        **kwargs: Any,
    ) -> "JsonDrawCacheStore":
        """기존 JSON 파일을 캐시 소스로 여는 팩토리.

        - ``cache_file`` 이 ``None`` 이면 기본 경로(``~/.lotto_cache/draws.json``).
        - 파일이 없으면 빈 스키마(``{"metadata": {"version": 1}, "draws": []}``)로 초기화한다.
        - 파일이 이미 존재하면 그대로 연다(덮어쓰지 않는다).
        """
        path = Path(cache_file) if cache_file is not None else DEFAULT_CACHE_FILE
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {"metadata": {"version": 1}, "draws": []},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return cls(path, **kwargs)

    # ------------------------------------------------------------------
    # 공개 API: 조회
    # ------------------------------------------------------------------
    def get(self, draw_no: int) -> DrawLookupResult:
        """단일 회차 조회. 존재하면 ``hit=True`` 와 원본 dict 사본을 반환한다."""
        self._validate_draw_no(draw_no)
        payload = self._read_payload()
        for draw in payload.get("draws", []) or []:
            if _coerce_draw_no(draw.get("drwNo")) == draw_no:
                return DrawLookupResult(hit=True, draw=dict(draw))
        return DrawLookupResult(hit=False, draw=None)

    def is_cached(self, draw_no: int) -> bool:
        """해당 회차가 캐시에 존재하는지 여부만 반환한다."""
        return self.get(draw_no).hit

    def get_recent_draws(self, n: int) -> list[dict[str, Any]]:
        """최신 ``n`` 개 회차를 ``drwNo`` 내림차순으로 반환한다."""
        if n <= 0:
            raise ValueError(f"n 은 양의 정수여야 한다: {n}")
        payload = self._read_payload()
        rows = list(payload.get("draws", []) or [])
        rows.sort(key=lambda d: _coerce_draw_no(d.get("drwNo")), reverse=True)
        return [dict(row) for row in rows[:n]]

    def load_draws(self, round_range: tuple[int, int]) -> list[dict[str, Any]]:
        """``[low..high]`` 구간에 속한 회차를 ``drwNo`` 오름차순으로 반환한다."""
        if not (isinstance(round_range, tuple) and len(round_range) == 2):
            raise ValueError(
                f"round_range 는 (low, high) 튜플이어야 한다: {round_range!r}"
            )
        low, high = round_range
        if not isinstance(low, int) or not isinstance(high, int):
            raise TypeError(f"round_range 는 int 쌍이어야 한다: {round_range!r}")
        if low <= 0 or high <= 0:
            raise ValueError(f"round_range 값은 양의 정수여야 한다: {round_range}")
        if low > high:
            raise ValueError(f"round_range 하한이 상한보다 크다: {round_range}")
        payload = self._read_payload()
        rows = [
            dict(d)
            for d in payload.get("draws", []) or []
            if low <= _coerce_draw_no(d.get("drwNo")) <= high
        ]
        rows.sort(key=lambda d: _coerce_draw_no(d["drwNo"]))
        return rows

    # ------------------------------------------------------------------
    # 공개 API: 상태와 무효화
    # ------------------------------------------------------------------
    def status(self) -> JsonCacheStatus:
        """현재 캐시의 신선도 상태를 요약한다.

        - ``metadata.last_fetched_at`` 이 없으면 ``missing_checkpoint``.
        - ``metadata.expires_at`` 이 있으면 해당 시각을 기준으로 만료를 판정한다.
        - 없으면 ``last_fetched_at + freshness_hours`` 를 기준으로 판정한다.
        - ``draws`` 개수가 ``required_draws`` 미만이면 ``insufficient_draws``.
        """
        payload = self._read_payload()
        metadata = payload.get("metadata", {}) or {}
        draws = payload.get("draws", []) or []

        total = len(draws)
        latest: int | None
        earliest: int | None
        if draws:
            drw_nos = [_coerce_draw_no(d.get("drwNo")) for d in draws]
            latest = max(drw_nos)
            earliest = min(drw_nos)
        else:
            latest = None
            earliest = None

        last_fetched_at = _parse_iso(metadata.get("last_fetched_at"))
        expires_at = _parse_iso(metadata.get("expires_at"))
        freshness_hours = _coerce_freshness_hours(
            metadata.get("freshness_hours"),
            fallback=self._default_freshness_hours,
        )

        reasons: list[StaleReason] = []
        if last_fetched_at is None and expires_at is None:
            reasons.append("missing_checkpoint")
        else:
            now = _now_in_tz(last_fetched_at or expires_at)
            if self._is_expired(
                now=now,
                last_fetched_at=last_fetched_at,
                expires_at=expires_at,
                freshness_hours=freshness_hours,
            ):
                reasons.append("expired_checkpoint")
        if total < self._required_draws:
            reasons.append("insufficient_draws")

        return JsonCacheStatus(
            total_draws=total,
            latest_drw_no=latest,
            earliest_drw_no=earliest,
            last_fetched_at=last_fetched_at,
            is_stale=bool(reasons),
            stale_reasons=tuple(reasons),
        )

    def invalidate(self, draw_no: int) -> bool:
        """특정 회차를 캐시에서 제거하고 파일에 반영한다.

        - 제거되었으면 ``True``, 회차가 없었으면 ``False`` 를 반환한다.
        """
        self._validate_draw_no(draw_no)
        payload = self._read_payload()
        draws = payload.get("draws", []) or []
        new_draws = [d for d in draws if _coerce_draw_no(d.get("drwNo")) != draw_no]
        removed = len(new_draws) < len(draws)
        if removed:
            payload["draws"] = new_draws
            self._write_payload(payload)
        return removed

    def save_draws(self, draws: Iterable[dict[str, Any]]) -> None:
        """전달된 회차 목록을 캐시에 병합해 저장한다.

        - 동일 ``drwNo`` 는 최신 입력으로 덮어쓴다.
        - 저장 후 ``metadata.last_fetched_at`` 을 현재 시각(UTC)으로 갱신한다.
        - 각 draw 는 최소 ``drwNo`` 필드를 가져야 한다.
        """
        if draws is None:
            raise ValueError("draws 는 None 일 수 없다")
        payload = self._read_payload()
        existing: dict[int, dict[str, Any]] = {
            _coerce_draw_no(d.get("drwNo")): dict(d)
            for d in payload.get("draws", []) or []
        }
        for draw in draws:
            if not isinstance(draw, dict):
                raise TypeError(f"draw 는 dict 여야 한다: {draw!r}")
            if "drwNo" not in draw:
                raise ValueError(f"draw 에 drwNo 가 없다: {draw!r}")
            existing[_coerce_draw_no(draw["drwNo"])] = dict(draw)
        payload["draws"] = sorted(existing.values(), key=lambda d: _coerce_draw_no(d["drwNo"]))
        metadata = payload.setdefault("metadata", {"version": 1})
        metadata["last_fetched_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._write_payload(payload)

    # ------------------------------------------------------------------
    # 공개 API: 파일 락
    # ------------------------------------------------------------------
    def acquire_lock(self, timeout: float = 0.1) -> int:
        """exclusive 파일 락을 획득한다.

        - ``timeout`` 초 내에 획득하지 못하면 `CacheLockTimeoutError` 를 발생시킨다.
        - 반환값(파일 디스크립터)은 `release_lock` 에 그대로 전달해야 한다.
        """
        if timeout < 0:
            raise ValueError(f"timeout 은 0 이상이어야 한다: {timeout}")
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_file), os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                    os.close(fd)
                    raise
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise CacheLockTimeoutError(
                        f"파일 락 획득 실패: path={self._lock_file}, timeout={timeout}s"
                    ) from None
                time.sleep(self._LOCK_POLL_INTERVAL)

    def release_lock(self, lock: int) -> None:
        """`acquire_lock` 이 반환한 핸들을 해제한다."""
        try:
            fcntl.flock(lock, fcntl.LOCK_UN)
        finally:
            os.close(lock)

    # ------------------------------------------------------------------
    # 내부 I/O
    # ------------------------------------------------------------------
    def _read_payload(self) -> dict[str, Any]:
        if not self._cache_file.exists():
            return {"metadata": {"version": 1}, "draws": []}
        try:
            text = self._cache_file.read_text(encoding="utf-8")
        except OSError as exc:
            self._logger.error("캐시 파일 읽기 실패: %s — %s", self._cache_file, exc)
            raise
        if not text.strip():
            return {"metadata": {"version": 1}, "draws": []}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            self._logger.error(
                "캐시 파일 파싱 실패: %s — %s", self._cache_file, exc
            )
            raise
        if not isinstance(parsed, dict):
            raise ValueError(
                f"캐시 JSON 루트는 object 여야 한다: {self._cache_file}"
            )
        return parsed

    def _write_payload(self, payload: dict[str, Any]) -> None:
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            self._logger.error("캐시 파일 쓰기 실패: %s — %s", self._cache_file, exc)
            raise

    @staticmethod
    def _validate_draw_no(draw_no: Any) -> None:
        if not isinstance(draw_no, int) or isinstance(draw_no, bool):
            raise TypeError(f"draw_no 는 정수여야 한다: {draw_no!r}")
        if draw_no <= 0:
            raise ValueError(f"draw_no 는 양의 정수여야 한다: {draw_no}")

    @staticmethod
    def _is_expired(
        *,
        now: datetime,
        last_fetched_at: datetime | None,
        expires_at: datetime | None,
        freshness_hours: float,
    ) -> bool:
        """만료 여부를 판정한다.

        - ``expires_at`` 이 있으면 해당 시각을 넘겼는지로만 판정한다.
        - 없으면 ``last_fetched_at + freshness_hours`` 를 기준으로 판정한다.
        - ``freshness_hours <= 0`` 은 "만료 판정을 하지 않음" 으로 해석한다.
        """
        if expires_at is not None:
            return now >= expires_at
        if last_fetched_at is None:
            return False
        if freshness_hours <= 0:
            return False
        return (now - last_fetched_at) >= timedelta(hours=freshness_hours)


def _parse_iso(value: Any) -> datetime | None:
    """ISO 8601 문자열을 timezone-aware datetime 으로 파싱한다.

    - ``value`` 가 문자열이 아니거나 파싱 실패 시 ``None``.
    - 타임존 정보가 없으면 UTC 로 간주한다(상호 비교 가능성을 위해).
    """
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _coerce_draw_no(value: Any) -> int:
    """회차 번호를 int 로 강제 변환한다. 실패 시 0 을 반환한다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_freshness_hours(value: Any, *, fallback: float) -> float:
    """metadata 의 freshness_hours 를 float 로 강제 변환한다."""
    if value is None:
        return fallback
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return fallback
    if hours < 0:
        return fallback
    return hours


def _now_in_tz(reference: datetime | None) -> datetime:
    """비교 대상 datetime 의 타임존에 맞춘 현재 시각을 반환한다."""
    tzinfo = reference.tzinfo if (reference is not None and reference.tzinfo) else timezone.utc
    return datetime.now(tz=tzinfo)


__all__ = [
    "CacheLockTimeoutError",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CACHE_FILE",
    "DrawLookupResult",
    "JsonCacheStatus",
    "JsonDrawCacheStore",
]
