"""WAV 녹음기(M5).

믹싱된 16kHz mono float32 스트림을 16-bit PCM WAV로 저장한다. 표준 라이브러리
``wave`` 모듈만 사용하므로 별도 오디오 I/O 의존성(soundfile/scipy)이 필요
없다(의존성 최소화). 저장 경로는 호출자가 ``meetings/<session_id>/`` 하위
경로로 전달한다(절대경로 하드코딩은 호출자에서 금지).
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from ..config import TARGET_SAMPLE_RATE

_SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM
_CHANNELS = 1            # mono


class WavRecorder:
    """16kHz mono 16-bit PCM WAV 파일을 점진적으로 기록한다."""

    def __init__(self) -> None:
        self._wave: wave.Wave_write | None = None
        self._path: Path | None = None

    def open(self, wav_path: Path) -> None:
        """WAV 파일을 쓰기 모드로 연다."""
        wav_path = Path(wav_path)
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        wf = wave.open(str(wav_path), "wb")
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH_BYTES)
        wf.setframerate(TARGET_SAMPLE_RATE)
        self._wave = wf
        self._path = wav_path

    def write(self, frames: np.ndarray) -> None:
        """16kHz mono float32 프레임을 16-bit PCM으로 추가한다."""
        if self._wave is None:
            return
        arr = np.asarray(frames, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            return
        pcm = np.clip(arr, -1.0, 1.0)
        pcm16 = (pcm * 32767.0).astype(np.int16)
        self._wave.writeframes(pcm16.tobytes())

    def close(self) -> None:
        """WAV 파일을 닫고 헤더를 마무리한다."""
        if self._wave is not None:
            try:
                self._wave.close()
            finally:
                self._wave = None
