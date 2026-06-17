# Architecture

This file is the living source of truth for the current architecture and workflow.
Update it whenever the design, workflow, interfaces, data flow, or implementation strategy changes.

## Metadata
- Last updated: 2026-06-13T08:05:00
- Status: active (build S0~S9 구현 완료, 헤드리스 셀프테스트 5/5 통과)
- Documentation language: 한국어 (실측 OS 로케일 `ko_KR`; 계약의 `c`는 미해석 POSIX 기본값. 프로젝트 전체 문서 세트가 한국어이므로 일관성을 위해 한국어로 작성)

## Current Design
- Summary: 마이크와 시스템오디오(WASAPI loopback)를 동시에 캡처·믹싱하면서 로컬 faster-whisper로 실시간 한국어 자막을 출력하고, 종료 시 원본 WAV·전사 텍스트(.txt/.md)·세션 메타데이터(JSON)를 `meetings/<session_id>/`에 자동 저장하는 PySide6 Windows 데스크톱 앱. 설계 원칙은 계층 격리 + 논블로킹 파이프라인(캡처→믹싱→청크큐→전사워커→UI 갱신을 큐/스레드로 분리).
- Core components (구현 완료):
  - M1 앱 셸/통합 (`app/main.py`) — `PipelineController`(QtWidgets 비의존 배선·상태 머신 소유: IDLE/INITIALIZING/RECORDING/STOPPING/SAVED/ERROR) + `main()` 엔트리포인트
  - M2 오디오 엔진 (`app/audio/capture.py`, `mixer.py`) — `CaptureThread`(장치 네이티브→16kHz mono 정규화), `AudioMixer`(두 스트림 평균 믹싱·청크 경계·RMS 레벨)
  - M3 전사 워커 (`app/stt/transcriber.py`, `worker.py`, `types.py`) — faster-whisper CUDA/CPU 분기(`devices.detect_compute_device`), VAD 청킹, `TranscribeWorker`(QThread, 전사기 주입)
  - M4 UI (`app/ui/main_window.py`, `widgets.py`) — 자막 패널, 장치/모델/언어 선택, 타이머, `LevelMeter`. PySide6 미설치 시 import는 성공·인스턴스화 시 명시적 오류
  - M5/M6 저장·세션 (`app/io/recorder.py`, `transcript_writer.py`, `session.py`) — `WavRecorder`(stdlib `wave`), `TranscriptWriter`(txt/md), `RecordingSession`(session.json)
  - M11 장치·설정 (`app/audio/devices.py`, `app/config.py`) — `enumerate_devices`, `detect_compute_device`, `AppSettings`, `resolve_save_root`
  - M7~M10 의존성/문서/패키징/셀프테스트 (`requirements.txt`, `README.md`, `build.py`, `meeting_stt.spec`, `tests/selftest_pipeline.py`)
  - Qt 호환 셰임 (`app/qt_compat.py`) — PySide6 유무와 무관하게 `QObject`/`Signal`/`QThread` 인터페이스 제공(헤드리스 import·셀프테스트 보장)
- Data flow: 마이크·loopback `CaptureThread`(각자 16kHz mono float32 정규화) → `AudioMixer`(평균 믹싱 + VAD 무음/`max_chunk_sec` 청크 경계 + RMS) → 청크 펌프 스레드가 `read_chunk`를 폴링해 `[WavRecorder.write]` + `[TranscribeWorker.enqueue]`로 분배 → `TranscribeWorker`(QThread, faster-whisper `vad_filter`) → `chunk_ready` Signal → `PipelineController`가 `TranscriptWriter.append` + UI 자막 append. 정지 시 캡처 stop → join → 펌프 정지 → 믹서 flush → worker drain → WAV close → txt/md flush → `RecordingSession` JSON 저장.
- Constraints: Windows WASAPI 전용(macOS/Linux 미지원). 저장 경로 절대경로 하드코딩 금지(`meetings/` 상대). 전사는 워커 스레드 전용 — UI 블로킹 금지. 타입 SSOT(RecordingSession/TranscriptChunk/AppSettings 단일 선언). 외부 webrtcvad 미사용(내장 vad_filter). 신규 스킬 forge 없이 기존 스택 reuse.
- Implementation decisions (build 단계 확정):
  - WAV 저장은 표준 라이브러리 `wave` 모듈 사용 — soundfile/scipy 의존성 제거(scope §2.1 대비 의존성 최소화).
  - 리샘플(장치 레이트→16kHz)은 캡처 측에서 수행 — 믹서 `push_*` 시그니처가 rate 인자를 받지 않는 고정 계약을 따르기 위함. 믹서는 16kHz mono를 가정해 믹싱·청킹.
  - 배선/상태 머신은 `PipelineController`(QtWidgets 비의존)로 캡슐화 — 헤드리스 셀프테스트(S8)가 배선을 end-to-end 검증 가능.
  - 전사기는 워커 생성자 주입 — 헤드리스에서 가짜 전사기로 enqueue→chunk_ready 배선 검증.
- Open questions: 없음(아키텍처는 feature-spec/implementation-design에서 변경 금지로 확정). 인터페이스 계약·구현 순서는 `docs/scope/2026-06-13-runnable-pyside6-stt-app-scope.md`로 고정.

## Synthetic audio headless selftest

The project includes a headless QA script at `scripts/synthetic_audio_headless_selftest.py`. It generates a deterministic mono PCM WAV file using only the Python standard library, validates the file header and signal characteristics, and writes a JSON report.

The selftest is intentionally independent from microphone, speaker, GUI, network, and model dependencies. It is suitable for CI smoke checks where the goal is to verify that the local Python runtime can create and inspect a known-good audio artifact before higher-level meeting STT workflows are exercised.

Default output is written to `.selftest/synthetic_audio/`. The output path can be changed with `--output-dir`.

> 앱 파이프라인 자체의 배선 검증은 `tests/selftest_pipeline.py`(M10, S8)가 담당한다. 위 `scripts/...` 셀프테스트는 런타임 오디오 아티팩트 생성/검증 스모크에 한정된다.

## Documentation Rule
- When the design changes, update this file in the same task.
- Append the matching entry to `docs/change_history.md` before closing the task.
- All generated or updated documents in this repository must use the language that matches OS language code `c`.
- Keep code, paths, commands, and API identifiers in their original form when needed.
