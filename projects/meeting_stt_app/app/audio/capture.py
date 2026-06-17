"""오디오 캡처 스레드(M2).

pyaudiowpatch(WASAPI)로 마이크 또는 시스템오디오 loopback 스트림을 열어
콜백으로 들어온 프레임을 16kHz mono float32로 정규화한 뒤 콜백 함수로
전달한다. 정규화(채널 mono화 + 리샘플)는 캡처 측에서 수행하므로 믹서는
16kHz mono를 가정할 수 있다(믹서 push 시그니처가 rate 인자를 받지 않음).

pyaudiowpatch가 없으면 ``start()``는 조용히 무동작한다(헤드리스 기동 보장).
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np

from ..config import TARGET_SAMPLE_RATE
from .mixer import resample_to_16k, to_mono_float32

# pyaudiowpatch가 콜백당 요청하는 프레임 수
FRAMES_PER_BUFFER = 1024


class CaptureThread:
    """단일 오디오 장치를 캡처해 정규화 프레임을 콜백으로 전달하는 스레드.

    Args:
        device_index: 열 장치의 PyAudio 인덱스. None이면 무동작.
        on_frames: 16kHz mono float32 프레임을 받는 콜백.
        loopback: loopback(시스템오디오) 장치 여부(로깅/구분용).
    """

    def __init__(
        self,
        device_index: Optional[int],
        on_frames: Callable[[np.ndarray], None],
        loopback: bool = False,
    ) -> None:
        self.device_index = device_index
        self.on_frames = on_frames
        self.loopback = loopback
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pa = None
        self._stream = None

    def start(self) -> None:
        """캡처를 시작한다. 장치가 없거나 pyaudiowpatch 미설치면 무동작."""
        if self.device_index is None:
            return
        try:
            import pyaudiowpatch  # noqa: F401
        except Exception:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import pyaudiowpatch as pyaudio

        try:
            self._pa = pyaudio.PyAudio()
            info = self._pa.get_device_info_by_index(self.device_index)
            src_rate = int(info.get("defaultSampleRate", TARGET_SAMPLE_RATE))
            channels = int(info.get("maxInputChannels", 1) or 1)
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=src_rate,
                frames_per_buffer=FRAMES_PER_BUFFER,
                input=True,
                input_device_index=self.device_index,
            )
            while not self._stop.is_set():
                try:
                    raw = self._stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                except Exception:
                    break
                pcm = np.frombuffer(raw, dtype=np.int16)
                mono = to_mono_float32(pcm, channels=channels)
                frames = resample_to_16k(mono, src_rate)
                if frames.size:
                    self.on_frames(frames)
        except Exception:
            # 장치 오류는 캡처 중단으로 처리(앱 전체는 계속 동작)
            return
        finally:
            self._close()

    def stop(self) -> None:
        """캡처를 정지하고 스트림이 완전히 닫힐 때까지 join한다."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _close(self) -> None:
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        try:
            if self._pa is not None:
                self._pa.terminate()
        except Exception:
            pass
        self._stream = None
        self._pa = None
