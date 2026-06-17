"""메인 윈도우(M4) — 자막 패널·장치/모델/언어 선택·타이머·레벨 미터.

``PipelineController``를 보유하고 시그널을 위젯에 연결한다. 전사·캡처는
컨트롤러(워커 스레드/캡처 스레드)에서 수행되므로 UI는 블로킹되지 않는다.

PySide6.QtWidgets가 없으면 모듈 import는 성공하되, ``MainWindow``
인스턴스화 시 명시적 오류를 낸다(헤드리스 기동 보장).
"""
from __future__ import annotations

from ..audio.devices import enumerate_devices
from ..main import STATE_RECORDING, STATE_STOPPING
from ..stt.types import TranscriptChunk
from .widgets import LevelMeter

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    HAS_QT_WIDGETS = True
except Exception:  # pragma: no cover
    HAS_QT_WIDGETS = False

# 모델/언어 선택지
_MODEL_SIZES = ["tiny", "base", "small", "medium"]
_LANGUAGES = [("한국어", "ko"), ("자동 감지", "auto")]


if HAS_QT_WIDGETS:

    class MainWindow(QMainWindow):
        """STT 회의록 앱의 메인 윈도우."""

        def __init__(self, controller) -> None:
            super().__init__()
            self.controller = controller
            self.setWindowTitle("회의록 STT")
            self.resize(720, 520)

            self._elapsed_sec = 0
            self._timer = QTimer(self)
            self._timer.setInterval(1000)
            self._timer.timeout.connect(self._tick)

            self._build_ui()
            self._populate_devices()
            self._connect_controller()
            self._apply_state(self.controller.state)

        # ── UI 구성 ─────────────────────────────────────────────────────
        def _build_ui(self) -> None:
            central = QWidget(self)
            root = QVBoxLayout(central)

            # 장치/모델/언어 선택 행
            controls = QHBoxLayout()
            self.mic_combo = QComboBox()
            self.loop_combo = QComboBox()
            self.model_combo = QComboBox()
            self.model_combo.addItems(_MODEL_SIZES)
            self.lang_combo = QComboBox()
            for label, _code in _LANGUAGES:
                self.lang_combo.addItem(label)
            controls.addWidget(QLabel("마이크"))
            controls.addWidget(self.mic_combo, 1)
            controls.addWidget(QLabel("시스템오디오"))
            controls.addWidget(self.loop_combo, 1)
            controls.addWidget(QLabel("모델"))
            controls.addWidget(self.model_combo)
            controls.addWidget(QLabel("언어"))
            controls.addWidget(self.lang_combo)
            root.addLayout(controls)

            # 레벨 미터 + 타이머 행
            meter_row = QHBoxLayout()
            self.level_meter = LevelMeter()
            self.elapsed_label = QLabel("00:00")
            meter_row.addWidget(QLabel("입력"))
            meter_row.addWidget(self.level_meter, 1)
            meter_row.addWidget(self.elapsed_label)
            root.addLayout(meter_row)

            # 자막 패널
            self.subtitle = QTextEdit()
            self.subtitle.setReadOnly(True)
            root.addWidget(self.subtitle, 1)

            # 시작/정지 버튼
            button_row = QHBoxLayout()
            self.start_button = QPushButton("녹음 시작")
            self.stop_button = QPushButton("정지 및 저장")
            self.start_button.clicked.connect(self._on_start)
            self.stop_button.clicked.connect(self._on_stop)
            button_row.addWidget(self.start_button)
            button_row.addWidget(self.stop_button)
            root.addLayout(button_row)

            self.setCentralWidget(central)
            self.statusBar().showMessage("대기 중")

        def _populate_devices(self) -> None:
            mics, loopbacks = enumerate_devices()
            self.mic_combo.clear()
            self.loop_combo.clear()
            if not mics:
                self.mic_combo.addItem("(장치 없음)", None)
            for d in mics:
                self.mic_combo.addItem(d.name, d.index)
            if not loopbacks:
                self.loop_combo.addItem("(장치 없음)", None)
            for d in loopbacks:
                self.loop_combo.addItem(d.name, d.index)

        def _connect_controller(self) -> None:
            self.controller.state_changed.connect(self._apply_state)
            self.controller.level_changed.connect(self._on_level)
            self.controller.chunk_ready.connect(self._on_chunk)
            self.controller.saved.connect(self._on_saved)
            self.controller.error.connect(self._on_error)

        # ── 버튼 핸들러 ─────────────────────────────────────────────────
        def _on_start(self) -> None:
            s = self.controller.settings
            s.mic_device_index = self.mic_combo.currentData()
            s.loopback_device_index = self.loop_combo.currentData()
            s.model_size = self.model_combo.currentText()
            s.language = _LANGUAGES[self.lang_combo.currentIndex()][1]
            s.save()
            self.subtitle.clear()
            self._elapsed_sec = 0
            self._update_elapsed_label()
            self.controller.start()
            self._timer.start()

        def _on_stop(self) -> None:
            self._timer.stop()
            self.controller.stop()

        # ── 컨트롤러 시그널 핸들러 ──────────────────────────────────────
        def _apply_state(self, state: str) -> None:
            recording = state == STATE_RECORDING
            self.start_button.setEnabled(not recording and state != STATE_STOPPING)
            self.stop_button.setEnabled(recording)
            for combo in (self.mic_combo, self.loop_combo, self.model_combo, self.lang_combo):
                combo.setEnabled(not recording and state != STATE_STOPPING)
            self.statusBar().showMessage(f"상태: {state}")

        def _on_level(self, level: float) -> None:
            self.level_meter.set_level(level)

        def _on_chunk(self, chunk: TranscriptChunk) -> None:
            self.subtitle.append(chunk.text)

        def _on_saved(self, session) -> None:
            self.statusBar().showMessage(f"저장 완료: {session.wav_path}")

        def _on_error(self, message: str) -> None:
            self.statusBar().showMessage(f"오류: {message}")

        # ── 타이머 ──────────────────────────────────────────────────────
        def _tick(self) -> None:
            self._elapsed_sec += 1
            self._update_elapsed_label()

        def _update_elapsed_label(self) -> None:
            m, s = divmod(self._elapsed_sec, 60)
            self.elapsed_label.setText(f"{m:02d}:{s:02d}")

        def closeEvent(self, event) -> None:  # noqa: N802 - Qt 시그니처
            if self.controller.state == STATE_RECORDING:
                self.controller.stop()
            super().closeEvent(event)

else:

    class MainWindow:  # type: ignore[no-redef]
        """PySide6 미설치 환경용 플레이스홀더."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("MainWindow는 PySide6 설치 환경에서만 사용할 수 있습니다.")
