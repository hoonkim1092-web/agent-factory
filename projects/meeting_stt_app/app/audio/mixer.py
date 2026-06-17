"""오디오 믹서(M2) — 두 16kHz mono 스트림을 합성하고 청크 경계를 결정한다.

캡처 스레드(``capture.py``)는 장치 네이티브 레이트/채널을 16kHz mono
float32로 정규화한 프레임을 ``push_mic``/``push_loopback``로 밀어 넣는다.
믹서는 두 버퍼를 시간순으로 합성(평균 믹싱)하고, VAD 무음 또는
``max_chunk_sec`` 도달 시 한 청크를 ``read_chunk``로 내보낸다. 동시에
RMS 레벨을 계산해 ``level_changed`` 시그널로 UI에 통지한다(약 50ms throttle).

``push_*``/``read_chunk``의 시그니처는 scope 계약(§3)으로 고정되어 있어
변경하지 않는다. 따라서 리샘플은 캡처 측에서 수행하고 믹서는 16kHz mono를
가정한다.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

import numpy as np

from ..config import TARGET_SAMPLE_RATE
from ..qt_compat import QObject, Signal

# 청크 경계 결정 상수
MIN_CHUNK_SEC = 1.0           # 무음 컷의 최소 청크 길이(너무 짧은 청크 방지)
SILENCE_RMS_THRESHOLD = 0.01  # 이 RMS 미만이면 무음으로 간주
SILENCE_TAIL_SEC = 0.4        # 청크 말미 이 길이가 무음이면 조기 컷
LEVEL_EMIT_INTERVAL_SEC = 0.05  # 레벨 미터 갱신 throttle(~50ms)


def to_mono_float32(frames: np.ndarray, channels: int = 1) -> np.ndarray:
    """임의 입력 프레임을 [-1, 1] 범위 mono float32로 변환한다.

    int16 PCM은 32768로 정규화하고, 다채널은 채널 평균으로 mono화한다.
    """
    arr = np.asarray(frames)
    if arr.dtype == np.int16:
        arr = arr.astype(np.float32) / 32768.0
    elif arr.dtype == np.int32:
        arr = arr.astype(np.float32) / 2147483648.0
    else:
        arr = arr.astype(np.float32)
    if channels > 1:
        arr = arr.reshape(-1, channels).mean(axis=1)
    else:
        arr = arr.reshape(-1)
    return arr


def resample_to_16k(frames: np.ndarray, src_rate: int) -> np.ndarray:
    """mono float32 프레임을 src_rate에서 16kHz로 선형 리샘플한다."""
    arr = np.asarray(frames, dtype=np.float32).reshape(-1)
    if src_rate == TARGET_SAMPLE_RATE or arr.size == 0:
        return arr
    n_out = int(round(arr.size * TARGET_SAMPLE_RATE / float(src_rate)))
    if n_out <= 0:
        return np.zeros(0, dtype=np.float32)
    src_idx = np.linspace(0.0, arr.size - 1, num=arr.size, dtype=np.float64)
    out_idx = np.linspace(0.0, arr.size - 1, num=n_out, dtype=np.float64)
    return np.interp(out_idx, src_idx, arr).astype(np.float32)


def rms(frames: np.ndarray) -> float:
    """프레임의 RMS(0~1 근처)를 반환한다."""
    arr = np.asarray(frames, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(arr))))


class AudioMixer(QObject):
    """두 16kHz mono 스트림을 합성하고 청크를 발행하는 믹서."""

    level_changed = Signal(float)

    def __init__(
        self,
        max_chunk_sec: float = 12.0,
        use_vad: bool = True,
        active_sources: int = 2,
    ) -> None:
        super().__init__()
        self.max_chunk_sec = max_chunk_sec
        self.use_vad = use_vad
        # 활성 캡처 소스 수(1=마이크 또는 loopback 단독, 2=둘 다). 이중 소스에서는
        # 정렬 가능한 만큼만 믹싱하고 나머지는 파트너가 도착할 때까지 버퍼에 유지한다.
        self._active_sources = max(1, int(active_sources))
        self._mic: deque[float] = deque()
        self._loop: deque[float] = deque()
        self._pending: list[np.ndarray] = []  # 아직 청크로 발행되지 않은 믹싱 결과
        self._pending_len = 0
        self._lock = threading.Lock()
        self._last_level_emit = 0.0

    # ── 입력 ────────────────────────────────────────────────────────────
    def push_mic(self, frames: np.ndarray) -> None:
        """마이크 16kHz mono float32 프레임을 추가한다."""
        self._push(self._mic, frames)

    def push_loopback(self, frames: np.ndarray) -> None:
        """시스템오디오(loopback) 16kHz mono float32 프레임을 추가한다."""
        self._push(self._loop, frames)

    def _push(self, buf: deque, frames: np.ndarray) -> None:
        arr = np.asarray(frames, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            return
        with self._lock:
            buf.extend(arr.tolist())
            self._drain_into_pending_locked()
        self._maybe_emit_level(arr)

    def _drain_into_pending_locked(self) -> None:
        """두 버퍼에서 시간 정렬 가능한 만큼을 평균 믹싱해 pending에 적재한다."""
        n = min(len(self._mic), len(self._loop))
        if n == 0:
            # 한쪽만 활성인 경우: 활성 스트림을 그대로 사용(상대는 0)
            single = self._mic if len(self._mic) > 0 and len(self._loop) == 0 else None
            if single is None:
                single = self._loop if len(self._loop) > 0 and len(self._mic) == 0 else None
            if single is None:
                return
            mixed = np.fromiter((single.popleft() for _ in range(len(single))),
                                dtype=np.float32)
            self._append_pending(mixed)
            return
        mic = np.fromiter((self._mic.popleft() for _ in range(n)), dtype=np.float32)
        loop = np.fromiter((self._loop.popleft() for _ in range(n)), dtype=np.float32)
        mixed = np.clip((mic + loop) * 0.5, -1.0, 1.0)
        self._append_pending(mixed)

    def _append_pending(self, mixed: np.ndarray) -> None:
        if mixed.size == 0:
            return
        self._pending.append(mixed)
        self._pending_len += mixed.size

    def _maybe_emit_level(self, frames: np.ndarray) -> None:
        now = time.monotonic()
        if now - self._last_level_emit < LEVEL_EMIT_INTERVAL_SEC:
            return
        self._last_level_emit = now
        self.level_changed.emit(rms(frames))

    # ── 출력 ────────────────────────────────────────────────────────────
    def read_chunk(self) -> Optional[np.ndarray]:
        """청크 경계에 도달했으면 16kHz mono 청크를 반환, 아니면 None."""
        max_samples = int(self.max_chunk_sec * TARGET_SAMPLE_RATE)
        min_samples = int(MIN_CHUNK_SEC * TARGET_SAMPLE_RATE)
        with self._lock:
            if self._pending_len == 0:
                return None
            if self._pending_len >= max_samples:
                return self._take_locked(max_samples)
            if self.use_vad and self._pending_len >= min_samples:
                buf = self._concat_pending_locked()
                tail = int(SILENCE_TAIL_SEC * TARGET_SAMPLE_RATE)
                if buf.size >= tail and rms(buf[-tail:]) < SILENCE_RMS_THRESHOLD:
                    return self._take_locked(buf.size)
            return None

    def flush(self) -> Optional[np.ndarray]:
        """정지 시 잔여 pending을 마지막 청크로 모두 반환한다(없으면 None)."""
        with self._lock:
            # 잔여 정렬 안 된 한쪽 버퍼도 마저 비운다
            self._drain_into_pending_locked()
            if self._pending_len == 0:
                return None
            return self._take_locked(self._pending_len)

    def _concat_pending_locked(self) -> np.ndarray:
        if not self._pending:
            return np.zeros(0, dtype=np.float32)
        if len(self._pending) > 1:
            self._pending = [np.concatenate(self._pending)]
        return self._pending[0]

    def _take_locked(self, n: int) -> np.ndarray:
        buf = self._concat_pending_locked()
        n = min(n, buf.size)
        out = buf[:n].copy()
        rest = buf[n:]
        self._pending = [rest] if rest.size else []
        self._pending_len = rest.size
        return out
