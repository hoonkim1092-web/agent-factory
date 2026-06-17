"""전사 타입 SSOT.

``TranscriptChunk``은 이 파일에서만 선언한다(타입 SSOT 규칙). 다른 모듈은
여기서 import 한다. 재선언 금지.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptChunk:
    """전사된 한 청크의 결과.

    Attributes:
        chunk_index: 0부터 증가하는 청크 순번.
        start_ts: 세션 시작 기준 청크 시작 시각(초).
        end_ts: 세션 시작 기준 청크 종료 시각(초).
        text: 전사된 텍스트.
        language: 감지/지정된 언어 코드("ko" 등).
        no_speech_prob: 무음 확률(0~1). 높을수록 음성 없음.
    """

    chunk_index: int
    start_ts: float
    end_ts: float
    text: str
    language: str
    no_speech_prob: float
