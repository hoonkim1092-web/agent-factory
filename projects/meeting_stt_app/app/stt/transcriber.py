"""faster-whisper 전사 코어(M3, S2 임계 경로).

CUDA 감지 시 ``cuda``/``float16``, 미감지 시 CPU ``int8``로 모델을 로드한다.
``transcribe_chunk``은 16kHz mono float32 오디오 한 청크를 받아 0개 이상의
``TranscriptChunk``을 반환한다.

faster-whisper(및 백엔드 ctranslate2)는 무겁고 배포 머신에만 설치되므로
모듈 import 시점이 아니라 ``Transcriber.__init__`` 시점에 lazily import 한다.
이로써 헤드리스 환경에서도 모듈 import는 성공한다.
"""
from __future__ import annotations

import numpy as np

from ..audio.devices import detect_compute_device
from ..config import TARGET_SAMPLE_RATE
from .types import TranscriptChunk

# 무음으로 간주해 버릴 임계 확률 — 이 값 이상이면 자막에 올리지 않는다(워커가 판단)
DEFAULT_NO_SPEECH_THRESHOLD = 0.6


class Transcriber:
    """faster-whisper 모델을 감싸 청크 단위 전사를 수행한다."""

    def __init__(self, model_size: str, language: str) -> None:
        self.model_size = model_size
        # "auto"는 faster-whisper에 None으로 전달해 자동 언어 감지
        self.language = language
        self._device, self._compute_type = detect_compute_device()
        self._chunk_index = 0
        self._offset_sec = 0.0

        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            model_size,
            device=self._device,
            compute_type=self._compute_type,
        )

    @property
    def device(self) -> str:
        return self._device

    def transcribe_chunk(self, audio: np.ndarray) -> list[TranscriptChunk]:
        """16kHz mono float32 오디오 한 청크를 전사한다.

        반환된 각 세그먼트는 세션 시작 기준의 누적 타임스탬프
        (``start_ts``/``end_ts``)를 갖는다. 빈 결과면 빈 리스트를 반환한다.
        """
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        duration = len(audio) / float(TARGET_SAMPLE_RATE)

        lang = None if self.language == "auto" else self.language
        segments, info = self._model.transcribe(
            audio,
            language=lang,
            vad_filter=True,
            beam_size=5,
        )

        detected_lang = getattr(info, "language", None) or self.language
        results: list[TranscriptChunk] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            chunk = TranscriptChunk(
                chunk_index=self._chunk_index,
                start_ts=self._offset_sec + float(seg.start),
                end_ts=self._offset_sec + float(seg.end),
                text=text,
                language=detected_lang,
                no_speech_prob=float(getattr(seg, "no_speech_prob", 0.0) or 0.0),
            )
            results.append(chunk)
            self._chunk_index += 1

        self._offset_sec += duration
        return results
