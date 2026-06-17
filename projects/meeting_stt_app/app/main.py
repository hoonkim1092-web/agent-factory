"""앱 셸 + end-to-end 통합 배선(M1, S7 — 본 모듈의 실질 완료 지점).

책임:
- ``QApplication`` 부트스트랩, ``AppSettings`` 로드, ``MainWindow`` 기동(``main()``).
- 캡처→믹싱→청크큐→전사워커→자막/저장의 end-to-end 배선을 단선 없이 조립.
- 녹음 상태 머신(IDLE/INITIALIZING/RECORDING/STOPPING/SAVED/ERROR) 소유.
- 저장 루트를 절대경로 하드코딩 없이 ``meetings/<session_id>/``로 해석.

배선 로직은 QtWidgets에 의존하지 않는 ``PipelineController``로 캡슐화하여
헤드리스 셀프테스트(S8)가 배선을 end-to-end로 검증할 수 있게 한다.
``MainWindow``(UI)는 이 컨트롤러를 보유하고 시그널을 위젯에 연결한다.
"""
from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .audio.capture import CaptureThread
from .audio.mixer import AudioMixer
from .config import AppSettings, resolve_save_root
from .io.recorder import WavRecorder
from .io.session import RecordingSession
from .io.transcript_writer import TranscriptWriter
from .qt_compat import QObject, Signal
from .stt.types import TranscriptChunk
from .stt.worker import TranscribeWorker

# 녹음 상태 머신 상태값 (매직 스트링 금지 — 단일 출처)
STATE_IDLE = "IDLE"
STATE_INITIALIZING = "INITIALIZING"
STATE_RECORDING = "RECORDING"
STATE_STOPPING = "STOPPING"
STATE_SAVED = "SAVED"
STATE_ERROR = "ERROR"

# 산출물 파일명
_WAV_NAME = "recording.wav"
_TXT_NAME = "transcript.txt"
_MD_NAME = "transcript.md"
_SESSION_NAME = "session.json"

# 펌프 폴링 주기(초)
_PUMP_INTERVAL_SEC = 0.02


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class PipelineController(QObject):
    """캡처→믹싱→전사→저장 파이프라인을 소유하고 상태 머신을 관리한다.

    QtWidgets 비의존 — 헤드리스에서 직접 구동·검증 가능. UI는 시그널을
    구독하고 ``start``/``stop``을 호출한다.
    """

    state_changed = Signal(str)            # 상태 머신 전이
    level_changed = Signal(float)          # RMS 레벨(레벨 미터)
    chunk_ready = Signal(object)           # TranscriptChunk (자막 패널)
    saved = Signal(object)                 # RecordingSession (저장 완료)
    error = Signal(str)                    # 오류 메시지

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        super().__init__()
        self.settings = settings or AppSettings.load()
        self.state = STATE_IDLE
        self._mixer: Optional[AudioMixer] = None
        self._worker: Optional[TranscribeWorker] = None
        self._recorder: Optional[WavRecorder] = None
        self._writer: Optional[TranscriptWriter] = None
        self._mic_capture: Optional[CaptureThread] = None
        self._loop_capture: Optional[CaptureThread] = None
        self._pump_thread: Optional[threading.Thread] = None
        self._pump_stop = threading.Event()
        self._session_dir: Optional[Path] = None
        self._session_id: str = ""
        self._started_at: str = ""
        self._start_monotonic: float = 0.0

    # ── 상태 ────────────────────────────────────────────────────────────
    @property
    def mixer(self) -> Optional[AudioMixer]:
        return self._mixer

    def _set_state(self, state: str) -> None:
        self.state = state
        self.state_changed.emit(state)

    # ── 시작 ────────────────────────────────────────────────────────────
    def start(self, transcriber=None) -> None:
        """녹음 파이프라인을 기동한다.

        Args:
            transcriber: 주입할 전사기. None이면 실제 ``Transcriber``를
                생성한다(faster-whisper 필요). 헤드리스 테스트는 가짜
                전사기를 주입한다.
        """
        if self.state in (STATE_INITIALIZING, STATE_RECORDING):
            return
        try:
            self._set_state(STATE_INITIALIZING)

            self._session_id = _new_session_id()
            save_root = resolve_save_root(self.settings)
            self._session_dir = Path(save_root) / self._session_id
            self._session_dir.mkdir(parents=True, exist_ok=True)

            self._recorder = WavRecorder()
            self._recorder.open(self._session_dir / _WAV_NAME)
            self._writer = TranscriptWriter()

            if transcriber is None:
                from .stt.transcriber import Transcriber

                transcriber = Transcriber(self.settings.model_size, self.settings.language)

            self._worker = TranscribeWorker(transcriber)
            self._worker.chunk_ready.connect(self._on_chunk)
            self._worker.start()

            self._mixer = AudioMixer(
                max_chunk_sec=self.settings.max_chunk_sec,
                use_vad=self.settings.use_vad,
            )
            self._mixer.level_changed.connect(self._on_level)

            self._mic_capture = CaptureThread(
                self.settings.mic_device_index, self._mixer.push_mic, loopback=False
            )
            self._loop_capture = CaptureThread(
                self.settings.loopback_device_index, self._mixer.push_loopback, loopback=True
            )
            self._mic_capture.start()
            self._loop_capture.start()

            self._started_at = _now_iso()
            self._start_monotonic = time.monotonic()

            self._pump_stop.clear()
            self._pump_thread = threading.Thread(target=self._pump, daemon=True)
            self._pump_thread.start()

            self._set_state(STATE_RECORDING)
        except Exception as exc:  # noqa: BLE001 - 시작 실패는 상태로 표면화
            self._set_state(STATE_ERROR)
            self.error.emit(str(exc))

    def _pump(self) -> None:
        """믹서에서 청크를 꺼내 녹음·전사 큐로 분배하는 펌프 루프."""
        while not self._pump_stop.is_set():
            chunk = self._mixer.read_chunk() if self._mixer else None
            if chunk is not None:
                self._dispatch_chunk(chunk)
            else:
                time.sleep(_PUMP_INTERVAL_SEC)

    def _dispatch_chunk(self, chunk) -> None:
        if self._recorder is not None:
            self._recorder.write(chunk)
        if self._worker is not None:
            self._worker.enqueue(chunk)

    # ── 시그널 핸들러 ───────────────────────────────────────────────────
    def _on_level(self, level: float) -> None:
        self.level_changed.emit(level)

    def _on_chunk(self, chunk: TranscriptChunk) -> None:
        if self._writer is not None:
            self._writer.append(chunk)
        self.chunk_ready.emit(chunk)

    # ── 정지 ────────────────────────────────────────────────────────────
    def stop(self) -> Optional[RecordingSession]:
        """녹음을 정지하고 산출물을 저장한 뒤 세션 메타데이터를 반환한다.

        정지 순서(scope §3.1 배선 불변식):
        캡처 stop → 펌프 정지 → 믹서 flush → 워커 drain → WAV close →
        txt/md flush → RecordingSession JSON 저장 → 저장 경로 표시.
        """
        if self.state != STATE_RECORDING:
            return None
        self._set_state(STATE_STOPPING)
        try:
            # 1) 캡처 stop + join
            if self._mic_capture is not None:
                self._mic_capture.stop()
            if self._loop_capture is not None:
                self._loop_capture.stop()

            # 2) 펌프 정지
            self._pump_stop.set()
            if self._pump_thread is not None:
                self._pump_thread.join(timeout=2.0)

            # 3) 잔여 read_chunk 소진 + 믹서 flush
            if self._mixer is not None:
                while True:
                    chunk = self._mixer.read_chunk()
                    if chunk is None:
                        break
                    self._dispatch_chunk(chunk)
                remainder = self._mixer.flush()
                if remainder is not None:
                    self._dispatch_chunk(remainder)

            # 4) 워커 drain (잔여 큐 전사까지 대기)
            if self._worker is not None:
                self._worker.stop_and_drain()

            # 5) WAV close
            if self._recorder is not None:
                self._recorder.close()

            # 6) txt/md flush
            txt_path = self._session_dir / _TXT_NAME
            md_path = self._session_dir / _MD_NAME
            if self._writer is not None:
                self._writer.flush(txt_path, md_path)

            # 7) RecordingSession JSON 저장
            session = self._build_session(txt_path, md_path)
            session.save_json(self._session_dir / _SESSION_NAME)

            self._set_state(STATE_SAVED)
            self.saved.emit(session)
            return session
        except Exception as exc:  # noqa: BLE001
            self._set_state(STATE_ERROR)
            self.error.emit(str(exc))
            return None

    def _build_session(self, txt_path: Path, md_path: Path) -> RecordingSession:
        duration = max(0.0, time.monotonic() - self._start_monotonic)
        return RecordingSession(
            session_id=self._session_id,
            started_at=self._started_at,
            ended_at=_now_iso(),
            wav_path=str(self._session_dir / _WAV_NAME),
            transcript_txt_path=str(txt_path),
            transcript_md_path=str(md_path),
            model_size=self.settings.model_size,
            language=self.settings.language,
            mic_device=str(self.settings.mic_device_index),
            loopback_device=str(self.settings.loopback_device_index),
            duration_sec=round(duration, 3),
        )


def main() -> int:
    """앱 엔트리포인트 — QApplication + MainWindow 기동."""
    from PySide6.QtWidgets import QApplication

    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    settings = AppSettings.load()
    controller = PipelineController(settings)
    window = MainWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
