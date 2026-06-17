"""전사 워커(M3) — 전사를 워커 스레드에서 수행한다.

UI 스레드가 ``enqueue``로 오디오 청크를 넣으면, 워커 스레드가 큐에서 꺼내
``Transcriber.transcribe_chunk``를 호출하고 결과를 ``chunk_ready`` 시그널로
메인 스레드에 통지한다. 전사는 **반드시 이 워커 스레드에서만** 수행되어
UI를 블로킹하지 않는다(scope §3.1 배선 불변식).

``Transcriber``는 생성자에서 주입한다. 이로써 faster-whisper 미설치
헤드리스 환경에서도 가짜(fake) 전사기를 주입해 enqueue→chunk_ready 배선을
end-to-end로 검증할 수 있다.
"""
from __future__ import annotations

import queue
from typing import Optional

import numpy as np

from ..qt_compat import QThread, Signal
from .types import TranscriptChunk

# 큐 종료 신호로 사용하는 센티넬
_SENTINEL = object()


class TranscribeWorker(QThread):
    """오디오 청크를 받아 전사 결과를 발행하는 QThread 워커."""

    chunk_ready = Signal(object)  # TranscriptChunk

    def __init__(self, transcriber, parent=None) -> None:
        super().__init__(parent)
        self._transcriber = transcriber
        self._queue: "queue.Queue" = queue.Queue()
        self._draining = False

    def enqueue(self, audio: np.ndarray) -> None:
        """전사할 16kHz mono 청크를 큐에 넣는다(논블로킹)."""
        if self._draining:
            return
        self._queue.put(np.asarray(audio, dtype=np.float32))

    def run(self) -> None:
        """워커 스레드 진입점 — 큐를 소진하며 전사한다."""
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            self._process(item)

    def _process(self, audio: np.ndarray) -> None:
        try:
            chunks = self._transcriber.transcribe_chunk(audio)
        except Exception:
            # 한 청크 전사 실패가 워커 전체를 죽이지 않도록 격리
            return
        for chunk in chunks:
            if isinstance(chunk, TranscriptChunk):
                self.chunk_ready.emit(chunk)

    def stop_and_drain(self) -> None:
        """잔여 큐를 모두 전사한 뒤 워커를 종료하고 join한다."""
        self._draining = True
        self._queue.put(_SENTINEL)
        self.wait()
