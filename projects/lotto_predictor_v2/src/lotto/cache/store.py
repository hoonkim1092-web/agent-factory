"""회차 데이터 로컬 JSON 캐시 저장소 구현."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from lotto.collector import CollectorAdapter, DrawRangeCollector, DrawResult
from lotto_predictor.collector import LottoCollector as PredictorLottoCollector

DEFAULT_CACHE_DIR = Path.home() / ".lotto_cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "draws.json"
DEFAULT_TTL_HOURS = 24.0
DEFAULT_LOCK_TIMEOUT = 1.0
LOCK_POLL_INTERVAL = 0.01


class CacheLockTimeoutError(Exception):
    """파일 락을 제한 시간 안에 획득하지 못했을 때 발생한다."""


class LottoCacheStore:
    """회차 데이터 로컬 캐시 저장소.

    JSON 파일은 `~/.lotto_cache/draws.json` 에 저장하며, `metadata.expires_at`
    를 기준으로 캐시 만료를 판단한다. 필요한 회차가 누락되었고 수집기가 주입된
    경우에는 수집기를 호출해 캐시를 보충한 뒤 다시 읽는다.
    """

    def __init__(
        self,
        cache_path: str | os.PathLike[str] | None = None,
        *,
        collector: DrawRangeCollector | PredictorLottoCollector | None = None,
        ttl_hours: float = DEFAULT_TTL_HOURS,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        if ttl_hours < 0:
            raise ValueError(f"ttl_hours 는 0 이상이어야 한다: {ttl_hours}")
        if lock_timeout < 0:
            raise ValueError(f"lock_timeout 은 0 이상이어야 한다: {lock_timeout}")

        self._cache_path = Path(cache_path) if cache_path is not None else DEFAULT_CACHE_FILE
        self._lock_path = self._cache_path.parent / f"{self._cache_path.name}.lock"
        self._ttl_hours = ttl_hours
        self._lock_timeout = lock_timeout
        self._collector = self._normalize_collector(collector)
        self._ensure_cache_file()

    def save_draws(self, draws: list[DrawResult]) -> None:
        """회차 목록을 캐시에 병합 저장한다.

        입력은 `DrawResult` 목록이어야 하며, 동일 회차 번호는 마지막 값을 우선한다.
        저장이 끝나면 `metadata.expires_at` 을 TTL 기준으로 다시 기록한다.
        """
        if not isinstance(draws, list):
            raise TypeError("draws 는 DrawResult 리스트여야 한다.")
        normalized = [self._coerce_draw(draw) for draw in draws]
        with self._locked_payload(write=True) as payload:
            existing = {
                self._coerce_round_no(item.get("drwNo")): dict(item)
                for item in payload.get("draws", [])
                if isinstance(item, dict)
            }
            for draw in normalized:
                existing[draw.drw_no] = draw.to_dict()
            payload["draws"] = [existing[key] for key in sorted(existing)]
            self._refresh_metadata(payload)

    def load_draws(self, round_range: tuple[int, int]) -> list[DrawResult]:
        """지정 회차 범위를 오름차순으로 읽는다.

        캐시가 만료되었거나 범위 내부 회차가 누락되었고 collector 가 주입된 경우,
        collector 에서 누락 범위를 가져와 저장한 뒤 결과를 반환한다.
        """
        start_round, end_round = self._validate_round_range(round_range)
        payload = self._read_payload()
        if self._needs_refresh(payload, start_round, end_round):
            self._collect_and_cache(start_round, end_round)
            payload = self._read_payload()

        filtered = [
            DrawResult.from_dict(item)
            for item in payload.get("draws", [])
            if isinstance(item, dict)
            and start_round <= self._coerce_round_no(item.get("drwNo")) <= end_round
        ]
        filtered.sort(key=lambda draw: draw.drw_no)
        return filtered

    def invalidate(self, round_no: int) -> None:
        """지정 회차를 캐시에서 제거하고 만료 시각을 다시 계산한다."""
        valid_round = self._validate_round_no(round_no)
        with self._locked_payload(write=True) as payload:
            draws = payload.get("draws", [])
            payload["draws"] = [
                item
                for item in draws
                if not (
                    isinstance(item, dict)
                    and self._coerce_round_no(item.get("drwNo")) == valid_round
                )
            ]
            self._refresh_metadata(payload)

    def is_cached(self, round_no: int) -> bool:
        """회차가 캐시에 존재하고 현재 만료되지 않았는지 확인한다."""
        valid_round = self._validate_round_no(round_no)
        payload = self._read_payload()
        if self._is_expired(payload):
            return False
        return any(
            isinstance(item, dict) and self._coerce_round_no(item.get("drwNo")) == valid_round
            for item in payload.get("draws", [])
        )

    def acquire_lock(self, timeout: float | None = None) -> int:
        """배타 파일 락을 획득하고 잠금 핸들을 반환한다."""
        limit = self._lock_timeout if timeout is None else timeout
        if limit < 0:
            raise ValueError(f"timeout 은 0 이상이어야 한다: {limit}")
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.monotonic() + limit
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
                        f"파일 락 획득에 실패했다: path={self._lock_path}, timeout={limit}"
                    ) from None
                time.sleep(LOCK_POLL_INTERVAL)

    def release_lock(self, lock_fd: int) -> None:
        """`acquire_lock()` 으로 얻은 파일 락을 해제한다."""
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    def _collect_and_cache(self, start_round: int, end_round: int) -> None:
        """collector 를 호출해 필요한 회차를 캐시에 채운다."""
        if self._collector is None:
            return
        collected = self._collector.collect_range(start_round, end_round)
        if collected:
            self.save_draws(collected)

    def _normalize_collector(
        self,
        collector: DrawRangeCollector | PredictorLottoCollector | None,
    ) -> DrawRangeCollector | None:
        if collector is None:
            return None
        if isinstance(collector, PredictorLottoCollector):
            return CollectorAdapter(collector)
        if hasattr(collector, "collect_range"):
            return collector
        raise TypeError("collector 는 collect_range(start_round, end_round)를 지원해야 한다.")

    def _ensure_cache_file(self) -> None:
        """캐시 파일이 없으면 기본 스키마로 초기화한다."""
        if self._cache_path.exists():
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps({"metadata": {"version": 1}, "draws": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_payload(self) -> dict[str, Any]:
        """캐시 JSON 파일을 읽어 파싱한다."""
        self._ensure_cache_file()
        try:
            text = self._cache_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OSError(f"캐시 파일을 읽지 못했다: {self._cache_path}") from exc
        if not text.strip():
            return {"metadata": {"version": 1}, "draws": []}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"캐시 JSON 파싱에 실패했다: {self._cache_path}") from exc
        if not isinstance(payload, dict):
            raise ValueError("캐시 JSON 루트는 object 여야 한다.")
        if "draws" not in payload or not isinstance(payload.get("draws"), list):
            payload["draws"] = []
        if "metadata" not in payload or not isinstance(payload.get("metadata"), dict):
            payload["metadata"] = {"version": 1}
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        """캐시 JSON 파일에 안전하게 기록한다."""
        if not isinstance(payload, dict):
            raise TypeError("payload 는 dict 여야 한다.")
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise OSError(f"캐시 파일을 쓰지 못했다: {self._cache_path}") from exc

    @contextmanager
    def _locked_payload(self, *, write: bool) -> Iterator[dict[str, Any]]:
        """파일 락을 잡은 상태로 payload 를 읽고, 필요 시 다시 저장한다."""
        lock_fd = self.acquire_lock()
        try:
            payload = self._read_payload()
            yield payload
            if write:
                self._write_payload(payload)
        finally:
            self.release_lock(lock_fd)

    def _needs_refresh(self, payload: dict[str, Any], start_round: int, end_round: int) -> bool:
        """캐시 만료 또는 범위 누락 여부를 판단한다."""
        if self._collector is None:
            return False
        if self._is_expired(payload):
            return True
        cached_rounds = {
            self._coerce_round_no(item.get("drwNo"))
            for item in payload.get("draws", [])
            if isinstance(item, dict)
        }
        expected = set(range(start_round, end_round + 1))
        return not expected.issubset(cached_rounds)

    def _is_expired(self, payload: dict[str, Any]) -> bool:
        """메타데이터의 `expires_at` 기준으로 캐시 만료 여부를 반환한다."""
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            return True
        expires_at = metadata.get("expires_at")
        if not isinstance(expires_at, str) or not expires_at.strip():
            return False
        try:
            parsed = datetime.fromisoformat(expires_at)
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return datetime.now(tz=parsed.tzinfo) >= parsed

    def _refresh_metadata(self, payload: dict[str, Any]) -> None:
        """저장 시점 기준 메타데이터를 갱신한다."""
        now = datetime.now(tz=timezone.utc)
        metadata = payload.setdefault("metadata", {"version": 1})
        metadata["version"] = int(metadata.get("version", 1) or 1)
        metadata["updated_at"] = now.isoformat()
        metadata["expires_at"] = (now + timedelta(hours=self._ttl_hours)).isoformat()

    @staticmethod
    def _validate_round_no(round_no: int) -> int:
        """회차 번호 입력을 검증하고 정규화한다."""
        if not isinstance(round_no, int) or isinstance(round_no, bool):
            raise TypeError(f"round_no 는 정수여야 한다: {round_no!r}")
        if round_no <= 0:
            raise ValueError(f"round_no 는 양의 정수여야 한다: {round_no}")
        return round_no

    def _validate_round_range(self, round_range: tuple[int, int]) -> tuple[int, int]:
        """회차 범위 입력을 검증한다."""
        if not isinstance(round_range, tuple) or len(round_range) != 2:
            raise ValueError("round_range 는 (start_round, end_round) 튜플이어야 한다.")
        start_round = self._validate_round_no(round_range[0])
        end_round = self._validate_round_no(round_range[1])
        if start_round > end_round:
            raise ValueError(
                f"start_round 가 end_round 보다 클 수 없다: {start_round}, {end_round}"
            )
        return start_round, end_round

    @staticmethod
    def _coerce_round_no(value: Any) -> int:
        """회차 번호를 정수로 변환한다."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _coerce_draw(draw: DrawResult | dict[str, Any]) -> DrawResult:
        """입력 회차를 `DrawResult` 로 정규화한다."""
        if isinstance(draw, DrawResult):
            return draw
        if isinstance(draw, dict):
            return DrawResult.from_dict(draw)
        raise TypeError(f"지원하지 않는 회차 타입이다: {type(draw).__name__}")


__all__ = ["CacheLockTimeoutError", "DEFAULT_CACHE_FILE", "LottoCacheStore"]
