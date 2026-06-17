# Implementation Tasks

## Metadata
- **work_item**: 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시
- **source_design**: implementation-design.md (회의록 STT 데스크톱 앱)
- **status**: draft
- **last_updated**: 2026-06-13

## Preconditions
- Python 3.11 가상환경이 준비되어 있고 `pip install`이 가능한 상태다.
- 대상 워크스페이스 `D:\warkSpaces\agent-factory\projects\meeting_stt_app`에 기존 초안(`feature-spec/feature-plan/implementation-tasks/task_execution_plan`, `.todo.md`, `project_board_state.json`, work_item 2건)이 존재하며 이를 출발점으로 이어받는다(§8).
- 확정 아키텍처(faster-whisper 로컬 고정, pyaudiowpatch WASAPI loopback, PySide6, numpy, PyInstaller onedir)는 변경 금지 제약이다(Brief constraints).
- 검증은 마이크 없는 헤드리스/CI 환경에서 합성 사인파 WAV로 수행 가능해야 한다(§5, §9).
- 절대경로 하드코딩 금지 — 저장 루트는 `meetings/` 하위로 해석한다(CLAUDE.md 절대경로 규칙, §6).
- 타입 SSOT: `RecordingSession`/`TranscriptChunk`/`AppSettings`는 각각 단일 파일에서만 선언한다(CLAUDE.md 타입 SSOT 규칙).

## Task Evidence
- **계약·산출물**: §6 Inputs and Outputs — 마이크/loopback 스트림 입력, 자막 패널 텍스트·원본 WAV·전사 `.txt/.md`·세션 메타 JSON 출력.
- **기능 요구**: §4 Functional Requirements — 동시 캡처·믹싱, 실시간 청크 전사, 논블로킹 워커, 자동 저장.
- **비기능 요구**: §5 Non-Functional Requirements — UI 비블로킹, 헤드리스 검증성, CUDA/CPU 자동 폴백.
- **예외 처리**: §7 Exceptions and Failure Scenarios — loopback 캡처 실패 시 마이크 단독 degrade, 장치 0개 graceful.
- **인수 기준**: §9 Acceptance Criteria — import 성공, 합성 WAV 1회 전사, end-to-end 배선, 패키징 스크립트 존재.
- **검증 초점**: Brief `verification_focus` 7항목(import·enumerate·합성 전사·e2e 배선·논블로킹·절대경로 부재·패키징).

## Task List

- [ ] **범위·계약·타입 SSOT 정의**
  - task_id: T-001
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - 11개 모듈(M1~M11)의 파일 경계·책임·의존이 표로 고정된다(§2, Design Planned Modules).
    - `RecordingSession`/`TranscriptChunk`/`AppSettings` 3개 dataclass의 단일 선언 파일과 필드가 §6 데이터 모델과 일치하게 확정된다.
    - `AudioMixer`/`Transcriber`/`TranscribeWorker`/`enumerate_devices` 내부 계약 시그니처가 동결된다(Design Interface Impact).
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('projects/meeting_stt_app/docs/work-items').exists() else 1)"`
  - artifacts: `docs/work-items/.../implementation-tasks.md`, 모듈 경계 표
  - estimated_complexity: low
  - implementation_hint: 타입은 `app/stt/types.py`(TranscriptChunk)·`app/io/session.py`(RecordingSession)·`app/config.py`(AppSettings)에 분산 선언하고 타 모듈은 import만 한다.

- [ ] **M11 장치/설정 레이어 구현**
  - task_id: T-002
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `enumerate_devices()`가 마이크·loopback 두 리스트를 반환하고 장치 0개에서도 빈 리스트·무예외다(§7).
    - `AppSettings` JSON 영속(load/save)이 동작하고 `save_root` 미설정 시 `meetings/` 기본 해석이 절대경로 리터럴 없이 이뤄진다(§6).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "devices or settings" -q`
  - artifacts: `app/audio/devices.py`, `app/config.py`
  - estimated_complexity: medium
  - implementation_hint: 비-Windows에서 `pyaudiowpatch` import를 가드로 감싸고 미지원 메시지로 빈 리스트 반환.

- [ ] **M6 세션 메타 + 공유 타입 구현**
  - task_id: T-003
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `RecordingSession` dataclass가 §6 필드 전체를 보유하고 `session.json` 직렬화/역직렬화가 라운드트립한다.
    - `TranscriptChunk` 타입이 `app/stt/types.py` 단일 선언으로 존재한다.
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "session_json" -q`
  - artifacts: `app/io/session.py`, `app/stt/types.py`
  - estimated_complexity: low
  - implementation_hint: `dataclasses.asdict` + `json.dump`로 직렬화, datetime은 ISO 문자열로 저장.

- [ ] **M2 오디오 엔진(캡처·믹싱) 구현**
  - task_id: T-004
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - 마이크·loopback 각각 캡처 스레드가 동작하고 16kHz mono 리샘플 후 믹싱된다(§4, Design Data Flow).
    - `read_chunk()`가 VAD 무음 경계 또는 `max_chunk_sec`(10~15초) 도달 시 청크를 반환하고 RMS `level_changed` Signal을 발행한다.
    - loopback 활성 스피커 부재 시 마이크 단독으로 degrade한다(§7).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "mixer or resample" -q`
  - artifacts: `app/audio/capture.py`, `app/audio/mixer.py`
  - estimated_complexity: high
  - implementation_hint: numpy로 리샘플·믹싱, 롤링 버퍼는 thread-safe deque; 캡처는 합성 프레임 주입이 가능하도록 push 인터페이스를 노출한다.

- [ ] **M3 전사 워커(faster-whisper) 구현**
  - task_id: T-005
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-003]
  - acceptance:
    - `Transcriber`가 CUDA 감지 시 `device=cuda/compute_type=float16`, 미감지 시 CPU `int8`로 자동 분기한다(§5).
    - `TranscribeWorker(QThread)`가 `chunk_queue`를 소비해 `transcribe(vad_filter=True)`로 `TranscriptChunk`를 만들고 `chunk_ready` Signal을 emit한다(§4).
    - 전사 호출이 UI 슬롯에서 직접 실행되지 않음이 코드 경로로 분리된다(§5, 논블로킹).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "transcriber_device_fallback" -q`
  - artifacts: `app/stt/transcriber.py`, `app/stt/worker.py`
  - estimated_complexity: high
  - implementation_hint: 모델 로드는 lazy/백그라운드, `language="ko"` 기본·`auto` 옵션, 큐 적체 임계 시 경고 Signal.

- [ ] **M5 저장 모듈(WAV·전사) 구현**
  - task_id: T-006
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-003]
  - acceptance:
    - 원본 WAV writer가 `meetings/<session_id>/`에 고품질 원본을 저장한다(§6).
    - `TranscriptWriter`가 청크를 누적해 `.txt`/`.md`를 flush한다(§6).
    - 저장 경로 해석에 `C:\`·`/Users/` 절대경로 리터럴이 없다(CLAUDE.md 규칙).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "recorder or transcript_writer" -q`
  - artifacts: `app/io/recorder.py`, `app/io/transcript_writer.py`
  - estimated_complexity: medium
  - implementation_hint: soundfile 또는 scipy.io.wavfile로 WAV write, 경로는 `Path.home()`/문서폴더/앱폴더 기반.

- [ ] **M4 UI(자막 패널·장치 선택·레벨 미터·타이머) 구현**
  - task_id: T-007
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-004, T-005]
  - acceptance:
    - 시작/정지 버튼, 마이크/시스템출력·모델·언어 드롭다운, 자막 append 패널, `QTimer` 타이머, RMS 레벨 미터, 저장 경로 표시가 구현된다(§4, §6).
    - `chunk_ready` Signal 수신 시 메인 스레드에서 자막을 append하며 UI가 블로킹되지 않는다(§5).
  - e2e_command: `QT_QPA_PLATFORM=offscreen pytest projects/meeting_stt_app/tests -k "main_window_smoke" -q`
  - artifacts: `app/ui/main_window.py`, `app/ui/widgets.py`
  - estimated_complexity: high
  - implementation_hint: Signal-Slot으로 워커와 결합, 헤드리스 테스트는 `QT_QPA_PLATFORM=offscreen`.

- [ ] **M1 앱 셸(엔트리포인트) 구현**
  - task_id: T-008
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-007]
  - acceptance:
    - `app/main.py`가 `QApplication` 부트스트랩 → 설정 로드 → MainWindow 기동까지 연결된다(Design Event Sequence Phase 1).
    - 모듈 import가 장치 없이 오류 없이 성공한다(§9).
  - e2e_command: `python -c "import app.main"`
  - artifacts: `app/main.py`, `app/__init__.py`
  - estimated_complexity: low
  - implementation_hint: 상태 머신(IDLE/INITIALIZING/RECORDING/STOPPING/SAVED/ERROR)을 메인 스레드 단일 소유로 둔다.

- [ ] **M7 requirements.txt 의존성 명세**
  - task_id: T-009
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile(또는 scipy), PyInstaller가 버전 고정으로 명세된다(§6, Brief tech_stack).
  - e2e_command: `pip install -r projects/meeting_stt_app/requirements.txt --dry-run`
  - artifacts: `requirements.txt`
  - estimated_complexity: low
  - implementation_hint: ctranslate2는 faster-whisper가 끌어오므로 명시 핀은 호환 범위만.

- [ ] **M8 README(설치/실행/시스템오디오 주의) 작성**
  - task_id: T-010
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - 설치·실행·사용법, WASAPI loopback 주의사항, 모델 사전 다운로드/오프라인 안내가 문서화된다(§6, Risks).
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('projects/meeting_stt_app/README.md').stat().st_size>500 else 1)"`
  - artifacts: `README.md`
  - estimated_complexity: low
  - implementation_hint: 활성 스피커 부재 시 loopback 캡처 실패 가능성·마이크 단독 degrade를 명시.

- [ ] **M9 PyInstaller onedir 패키징 스펙/스크립트 구현**
  - task_id: T-011
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-008]
  - acceptance:
    - `build.py`/`meeting_stt.spec`가 존재하고 ctranslate2 DLL·모델 가중치를 `binaries`/`datas`/`hiddenimports`로 명시 번들한다(§9, Risks).
    - 패키징 절차가 README에 문서화된다.
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('projects/meeting_stt_app/meeting_stt.spec').exists() else 1)"`
  - artifacts: `build.py`, `meeting_stt.spec`
  - estimated_complexity: medium
  - implementation_hint: onefile 금지(native DLL 로딩 이슈) — onedir 고정.

- [ ] **end-to-end 파이프라인 배선(통합)**
  - task_id: T-012
  - owner_role: backend_dev
  - phase: integrate
  - depends_on: [T-004, T-005, T-006, T-007, T-008]
  - acceptance:
    - 캡처 → AudioMixer → chunk_queue → TranscribeWorker → 자막 append → TranscriptWriter → Recorder → RecordingSession이 코드상 end-to-end 연결된다(§9, Design Data Flow).
    - 정지 시 잔여 버퍼 flush → WAV close → `.txt/.md` flush → `session.json` 저장 순서가 보장된다(Design Phase 4~5).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "e2e_wiring" -q`
  - artifacts: 통합 배선 코드, handoff 메모
  - estimated_complexity: high
  - implementation_hint: 새 파라미터가 production 호출 경로(`app/main.py`)까지 흘러가는지 grep으로 확인(파이프라인 배포 동등성 규칙).

- [ ] **M10 합성 오디오 헤드리스 셀프테스트 구현(통합)**
  - task_id: T-013
  - owner_role: qa_engineer
  - phase: integrate
  - depends_on: [T-012]
  - acceptance:
    - 16kHz mono 합성 사인파/샘플 WAV를 STT 파이프라인에 통과시켜 `TranscriptChunk` ≥1을 생성한다(§9, verification_focus).
    - 장치 0개 환경에서도 enumerate·캡처 경로가 graceful하게 진행된다(§7).
  - e2e_command: `python projects/meeting_stt_app/tests/selftest_pipeline.py`
  - artifacts: `tests/selftest_pipeline.py`
  - estimated_complexity: medium
  - implementation_hint: numpy로 사인파 생성 후 mixer push 인터페이스에 직접 주입, 마이크/스피커 미사용 경로.

- [ ] **검증: import 스모크 + 장치 enumerate graceful**
  - task_id: T-014
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-013]
  - acceptance:
    - 전 모듈 import가 장치 없이 무예외 성공한다(§9).
    - `enumerate_devices()`가 장치 0개에서 빈 리스트·무예외다(§7).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "import_smoke or enumerate_graceful" -q`
  - artifacts: 검증 로그
  - estimated_complexity: low
  - implementation_hint: `QT_QPA_PLATFORM=offscreen`로 UI import 포함.

- [ ] **검증: 합성 WAV 1회 전사 성공 + 논블로킹**
  - task_id: T-015
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-013]
  - acceptance:
    - 합성 WAV가 faster-whisper 파이프라인을 1회 전사 성공한다(§9 핵심 통과 조건).
    - 전사 호출이 UI 슬롯에서 직접 실행되지 않음이 코드 경로로 확인된다(§5).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "synthetic_transcribe or nonblocking" -q`
  - artifacts: 검증 로그
  - estimated_complexity: medium
  - implementation_hint: 모델은 `tiny`로 다운그레이드해 CI 시간을 단축할 수 있음.

- [ ] **검증: e2e 저장 흐름 + 절대경로 부재**
  - task_id: T-016
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-012]
  - acceptance:
    - 합성 스트림 → WAV + `.txt`/`.md` + `session.json`이 `meetings/<session_id>/`에 생성된다(§9).
    - 저장 경로에 `C:\`·`/Users/` 절대경로 리터럴이 없다(정적 검사, CLAUDE.md 규칙).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "e2e_save_flow or no_hardcoded_abspath" -q`
  - artifacts: 생성 산출물, 검증 로그
  - estimated_complexity: medium
  - implementation_hint: 정적 검사는 소스에서 절대경로 패턴 grep으로 0건 단언.

- [ ] **검증: 패키징 스크립트 존재 + 빌드 후 셀프테스트**
  - task_id: T-017
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-011, T-013]
  - acceptance:
    - `build.py`/`meeting_stt.spec`가 존재하고 패키징 절차가 문서화되어 있다(§9).
    - onedir 빌드 산출물에서 셀프테스트 1회 전사가 재실행되어 ctranslate2 DLL·모델 번들 무결성이 확인된다(Design Test Strategy 7).
  - e2e_command: `pytest projects/meeting_stt_app/tests -k "packaging_artifacts_exist" -q`
  - artifacts: `dist/` 산출물(빌드 시), 검증 로그
  - estimated_complexity: medium
  - implementation_hint: CI에서 실제 빌드가 무거우면 스펙 존재·문서화만 게이트하고 빌드 검증은 수동 단계로 분리.

- [ ] **검증·마감: handoff·잔여 리스크 기록**
  - task_id: T-018
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-014, T-015, T-016, T-017]
  - acceptance:
    - 7개 verification_focus 항목 결과가 정리되고 잔여 리스크·후속 작업이 기록된다(Design Risks, §9).
    - 다음 작업자가 이어받을 handoff 메모가 작성된다.
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('projects/meeting_stt_app/HANDOFF.md').stat().st_size>500 else 1)"`
  - artifacts: `HANDOFF.md`(handoff 메모 + 잔여 리스크 목록)
  - estimated_complexity: low
  - implementation_hint: loopback 캡처 실패·믹싱 드리프트·CPU 백로그·모델 다운로드 지연 4대 리스크의 현재 완화 상태를 명시.

## Blockers
- **B-1 (T-005)**: faster-whisper 모델 최초 다운로드가 오프라인 CI에서 차단될 수 있음 → `tiny` 모델 사전 캐시 또는 번들 필요(Risks).
- **B-2 (T-004)**: pyaudiowpatch WASAPI loopback은 Windows·활성 스피커 의존 → 헤드리스에서는 합성 주입 경로로만 검증(§7).
- **B-3 (T-017)**: 실제 PyInstaller onedir 빌드는 시간·디스크 비용이 커 CI 자동화 시 별도 잡으로 분리해야 할 수 있음.
- **B-4 (T-018)**: handoff·잔여 리스크 메모는 자동 존재 검사(`HANDOFF.md` 크기 게이트)로 산출물 유무만 보증한다. 7개 verification_focus 결과의 사실 정합·서술 정확성은 자동 e2e로 보증되지 않으므로 머지 전 사람의 수동 검토가 추가로 필요하다.

## Rollback Sign-Off
- 신규 외부 프로젝트(`projects/meeting_stt_app`)로 기존 Agent Factory 코어에 영향 없음(`blast_radius: isolated`).
- 롤백은 `projects/meeting_stt_app/` 신규 파일 제거로 완결되며 기존 데이터·스키마 마이그레이션이 없어 역방향 작업이 불필요(Design Migration Requirement).
- 각 build 태스크는 독립 모듈 파일 단위이므로 개별 태스크 단위 되돌림이 가능하다.
- Sign-Off 조건: T-014~T-017 전부 통과 + T-018 handoff 기록 완료 시 머지 승인.

## Definition Of Done
- 앱이 import 오류 없이 기동된다(헤드리스: 모듈 import + 장치 enumerate graceful + 합성 WAV STT 1회 전사 성공) — T-014, T-015 통과(§9).
- 녹음 시작 → 실시간 자막 append → 정지 → WAV + 전사 `.txt/.md` + `session.json` 저장 흐름이 코드상 end-to-end 연결된다 — T-012, T-016 통과(§9).
- 전사 워커가 UI 스레드를 블로킹하지 않는다(큐/스레드 분리) — T-015 통과(§5).
- 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위로 생성된다 — T-016 통과(CLAUDE.md 규칙).
- PyInstaller onedir 빌드 스크립트가 존재하고 패키징 절차가 문서화된다 — T-011, T-017 통과(§9).
- `RecordingSession`/`TranscriptChunk`/`AppSettings` 타입이 각각 단일 파일 선언으로 유지된다(타입 SSOT).
- 잔여 리스크·후속 작업·handoff가 기록된다 — T-018 완료.