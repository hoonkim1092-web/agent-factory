# Implementation Tasks

## Metadata

- **work_item**: 회의-음성-마이크-시스템오디오-wasapi-loopback-동시녹음-faster-whisper-실시간-stt-pyside6-데스크톱-앱
- **source_design**: implementation-design.md (회의록 STT 데스크톱 앱)
- **status**: draft
- **last_updated**: 2026-06-13

---

## Preconditions

- Python 3.11 환경이 준비되어 있고 가상환경 생성이 가능하다(ctranslate2/onnxruntime wheel 호환성 — design §Compatibility Considerations).
- 타깃 경로 `D:\warkSpaces\agent-factory\projects\meeting_stt_app` 가 작업 루트로 고정되며, 모든 산출물은 이 하위에 생성한다.
- 저장 경로는 절대경로 리터럴 없이 `meetings/` 하위로 해석된다(brief constraint, design §State And Data Model).
- WASAPI loopback은 Windows 전용이며, 비-Windows/헤드리스에서는 캡처 모듈을 지연 로딩하여 import만 통과시킨다(design §Compatibility Considerations).
- 첫 실행 시 faster-whisper small 모델(~500MB) 다운로드가 필요하며, 헤드리스 검증은 합성 사인파 WAV로 STT 경로만 검증한다(design §Test Strategy).
- 모듈 의존 방향은 단방향 `main → ui → {audio, stt, persistence} → config` 를 유지하며, 엔진은 UI를 import하지 않는다(design §Planned Modules).

---

## Task Evidence

- 검증 기준은 brief의 `verification_focus` 7항목을 SSOT로 채택한다(design §Design Evidence).
- 헤드리스 셀프테스트(`python scripts/selftest.py`)가 필수 e2e이며, 합성 WAV가 STT 파이프라인을 1회 통과해 `TranscriptChunk` 를 반환해야 한다.
- 호출 경로 통합 테스트는 stub-only 금지 — 최소 1개 실제 실행 경로를 포함한다(design §Test Strategy 4, Episode Hint).
- approval-gate `status=completed` 는 파일 존재 + 금지토큰(절대경로 리터럴) 0 + e2e exit 0 을 모두 충족할 때만 인정한다.
- 데이터 계약: `AudioConfig`/`RecordingSession`/`TranscriptChunk` 는 단일 파일(`app/config.py`)에서만 선언하고 타 모듈은 import한다(타입 SSOT 규칙).

---

## Task List

- [ ] 패키지 구조와 모듈 인터페이스 계약을 고정한다
  - task_id: T-001
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `app/` 패키지 트리(`app/main.py`, `app/config.py`, `app/audio/`, `app/stt/`, `app/ui/`, `app/persistence.py`)와 `scripts/`, 패키징 파일 목록이 문서로 확정된다(design §Planned Modules).
    - `AudioConfig`/`RecordingSession`/`TranscriptChunk` 필드와 모듈 간 함수 시그니처가 design §Interface Impact 계약과 일치하게 명시된다.
    - 모듈 의존 방향(`main → ui → {audio, stt, persistence} → config`)과 단방향 규칙이 기록된다.
  - e2e_command: `python -c "import pathlib; assert pathlib.Path('docs/interface_contract.md').exists()"`
  - artifacts: docs/interface_contract.md
  - estimated_complexity: low
  - implementation_hint: design §Interface Impact의 dataclass·함수 시그니처를 그대로 계약 문서로 옮기고, 타입은 `app/config.py` 단일 선언으로 고정(타입 SSOT).

- [ ] `app/config.py` — 설정·경로·디바이스 감지를 구현한다
  - task_id: T-002
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `AudioConfig`/`RecordingSession`/`TranscriptChunk` dataclass가 design §State And Data Model 필드대로 단일 선언된다.
    - `detect_device()` 가 CUDA 감지 시 `("cuda","float16")`, 미감지 시 `("cpu","int8")` 을 반환한다(brief constraint).
    - `save_dir` 가 ①사용자설정 → ②`Path.home()/"Documents"/"meetings"` → ③`Path(__file__).resolve().parent.parent/"meetings"` 순으로 해석되며 절대경로 리터럴이 없다(design §State And Data Model).
  - e2e_command: `python -c "from app.config import detect_device; assert detect_device()[0] in ('cuda','cpu')"`
  - artifacts: app/config.py
  - estimated_complexity: low
  - implementation_hint: CUDA 감지는 `try: import torch / ctranslate2 capability` 후 실패 시 except로 CPU 폴백. 경로는 리터럴 금지 — `Path.home()`/`Path(__file__)` 만 사용.

- [ ] `app/audio/capture.py` — 마이크·loopback 캡처 스레드와 장치 enumerate를 구현한다
  - task_id: T-003
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `enumerate_devices()` 가 `(mics, loopbacks)` 를 반환하고, 장치 0개 환경에서도 예외 없이 빈 목록을 반환한다(verification_focus #2).
    - `CaptureThread` 가 `target_device`, `out_buffer`, `stop_event` 로 16kHz mono 리샘플 후 버퍼에 push한다(design §Data Flow).
    - pyaudiowpatch import가 모듈 최상단이 아닌 지연 로딩으로 처리되어 비-Windows에서 모듈 import가 통과한다(verification_focus #1).
  - e2e_command: `python -c "from app.audio.capture import enumerate_devices; m,l=enumerate_devices(); assert isinstance(m,list) and isinstance(l,list)"`
  - artifacts: app/audio/capture.py
  - estimated_complexity: high
  - implementation_hint: `get_default_wasapi_loopback()` 사용. 리샘플은 정수비(48k→16k) 우선, 비정수비는 `scipy.signal.resample_poly`. 플랫폼 가드로 비-Windows import 안전화.

- [ ] `app/audio/mixer.py` — MixBuffer 믹싱·롤링 버퍼·청킹을 구현한다
  - task_id: T-004
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `MixBuffer.push(samples, source)` 가 두 스트림을 16kHz 타임라인으로 합산하며 길이 불일치 시 zero-pad로 정렬한다(design §Compatibility Considerations).
    - `pop_chunk()` 가 VAD 무음 또는 최대 길이(10~15초) 도달 시에만 청크를 반환하고, 그 외에는 `None` 을 반환한다(design §Data Flow).
    - 청크 간 overlap(0.5~1초)이 유지되어 단어 잘림이 완화된다(design §Risks).
  - e2e_command: `pytest tests/test_mixer.py -q`
  - artifacts: app/audio/mixer.py, tests/test_mixer.py
  - estimated_complexity: medium
  - implementation_hint: numpy 누적 버퍼 + 청크 경계 인덱스 산출. maxlen·overlap은 명명 상수로 고정(매직넘버 금지).

- [ ] `app/stt/worker.py` — faster-whisper 전사 워커를 구현한다
  - task_id: T-005
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002, T-004]
  - acceptance:
    - `TranscribeWorker(cfg, chunk_queue)` 가 `chunk_queue` 를 blocking get으로 소비하며 UI를 블로킹하지 않는다(brief constraint).
    - `model.transcribe(chunk, vad_filter=True, language=cfg.language)` 결과로 `TranscriptChunk` 를 생성해 `transcribed` Signal을 emit한다(design §Event Sequence Phase 3).
    - 모델 로드 실패 시 CPU int8 경로로 폴백되고 폴백 사실이 상태로 노출된다(verification_focus #5).
  - e2e_command: `pytest tests/test_worker.py -q`
  - artifacts: app/stt/worker.py, tests/test_worker.py
  - estimated_complexity: high
  - implementation_hint: QObject 기반, 모델 로드는 워커 스레드 사전 워밍업. `finished` Signal로 큐 drain 종료 통지. 모델 다운로드 캐시 경로는 `HF_HOME` 존중.

- [ ] `app/persistence.py` — WAV·전사·세션 저장 모듈을 구현한다
  - task_id: T-006
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002]
  - acceptance:
    - `save_wav(buf, path, sample_rate)` 가 누적 원본을 `meetings/<session_id>/audio.wav` 로 저장한다(design §Event Sequence Phase 4).
    - `save_transcript(chunks, txt_path, md_path)` 가 `.txt`(플레인)·`.md`(타임스탬프·세션 헤더)로 직렬화한다(deliverable).
    - `save_session(session, path)` 가 `session.json` 메타데이터를 기록하며, 모든 경로가 절대경로 리터럴 없이 `meetings/` 하위로 해석된다(verification_focus #6).
  - e2e_command: `pytest tests/test_persistence.py -q`
  - artifacts: app/persistence.py, tests/test_persistence.py
  - estimated_complexity: medium
  - implementation_hint: WAV I/O는 soundfile. session_id는 시작 시각 기반 슬러그. 경로는 T-002의 `save_dir` 해석을 재사용.

- [ ] `app/ui/main_window.py` · `app/ui/widgets.py` — 메인 윈도우와 자막·레벨 위젯을 구현한다
  - task_id: T-007
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-003, T-005, T-006]
  - acceptance:
    - 시작/정지 버튼, 마이크·loopback 장치 드롭다운, 모델 크기·언어 선택, 녹음 타이머, 저장 경로 표시가 배치된다(brief UI 요구).
    - 자막 패널이 워커의 `transcribed` Signal 슬롯에 연결되어 청크 단위로 append되고, 레벨 미터가 갱신된다(design §Event Sequence Phase 3).
    - 장치 enumerate 결과가 빈 목록이면 시작 버튼 비활성화 + 안내 라벨을 표시한다(design §Event Sequence Phase 1).
  - e2e_command: `python -c "import importlib; importlib.import_module('app.ui.main_window'); importlib.import_module('app.ui.widgets')"`
  - artifacts: app/ui/main_window.py, app/ui/widgets.py
  - estimated_complexity: high
  - implementation_hint: UI 스레드에서만 `AppState` 전이. 위젯은 엔진을 호출하되 엔진은 UI를 import하지 않음(헤드리스 셀프테스트가 엔진 직접 구동 가능해야 함).

- [ ] `app/main.py` — 진입점과 `--selftest` 분기를 구현한다
  - task_id: T-008
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-007]
  - acceptance:
    - QApplication 부트스트랩 후 MainWindow를 생성하고 `AppState` 상태머신을 초기화한다(design §State And Data Model).
    - `--selftest` 인자 시 GUI를 띄우지 않고 헤드리스 셀프테스트 경로로 분기한다(design §Planned Modules).
    - import 오류 없이 기동 경로가 구성된다(verification_focus #1).
  - e2e_command: `python -m app.main --selftest`
  - artifacts: app/main.py
  - estimated_complexity: medium
  - implementation_hint: `--selftest` 는 `scripts/selftest.py` 호출 또는 동일 로직 재사용. argparse로 분기.

- [ ] `requirements.txt` — 의존성 명세를 작성한다
  - task_id: T-009
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile/scipy, PyInstaller가 버전 핀과 함께 명시된다(brief 산출물).
    - Python 3.11 환경에서 `pip install -r requirements.txt` 가 의존성 충돌 없이 해석된다(design §Compatibility Considerations).
  - e2e_command: `python -m pip install --dry-run -r requirements.txt`
  - artifacts: requirements.txt
  - estimated_complexity: low
  - implementation_hint: ctranslate2/onnxruntime는 faster-whisper 전이 의존. wheel 호환을 위해 Python 3.11 가정.

- [ ] `build.spec` · `build.py` — PyInstaller onedir 패키징을 구현한다
  - task_id: T-010
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-008, T-009]
  - acceptance:
    - `build.spec` 가 ctranslate2/onnxruntime 네이티브 DLL과 모델을 `binaries`/`datas` 로 명시하고 onedir 모드를 채택한다(design §Risks).
    - `python build.py` 가 `dist/` 하위에 실행 산출물을 생성한다(verification_focus #7).
  - e2e_command: `python build.py && python -c "import pathlib,glob; assert glob.glob('dist/**/*', recursive=True)"`
  - artifacts: build.spec, build.py
  - estimated_complexity: high
  - implementation_hint: onefile 금지(DLL 누락·추출 오버헤드). 빌드 후 smoke 실행을 build.py 말미에 옵션으로 포함.

- [ ] `README.md` — 설치·실행·시스템오디오 주의사항 문서를 작성한다
  - task_id: T-011
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-009]
  - acceptance:
    - 설치·실행·사용법, WASAPI loopback 캡처 주의사항, 오프라인 모델 캐시 배치 절차가 문서화된다(brief 산출물, design §Compatibility Considerations).
    - PyInstaller 패키징 절차(T-010)가 명시적으로 기술된다(verification_focus #7).
  - e2e_command: `python -c "t=open('README.md',encoding='utf-8').read(); assert 'loopback' in t.lower() and 'pyinstaller' in t.lower()"`
  - artifacts: README.md
  - estimated_complexity: low
  - implementation_hint: 기본 스피커 변경 시 loopback 실패 폴백, CPU/GPU 폴백, 모델 다운로드 지연을 사용자 안내로 포함.

- [ ] `scripts/selftest.py` — 합성 오디오 헤드리스 셀프테스트를 구현한다
  - task_id: T-012
  - owner_role: qa_engineer
  - phase: build
  - depends_on: [T-005, T-006]
  - acceptance:
    - numpy 사인파 → 16kHz mono WAV 생성 후 `TranscribeWorker` 를 UI 없이 직접 구동해 `transcribe` 1회가 성공하고 `TranscriptChunk` 를 반환한다(design §Test Strategy 1).
    - `detect_device()` 호출로 device 튜플을 확인하고, 성공 시 exit code 0을 반환한다(verification_focus #3,#5).
    - 오디오 장치 없이도 STT 경로만으로 통과한다(헤드리스 변형 흐름).
  - e2e_command: `python scripts/selftest.py`
  - artifacts: scripts/selftest.py
  - estimated_complexity: medium
  - implementation_hint: enumerate를 건너뛰고 합성 WAV를 직접 `chunk_queue` 에 주입(Phase 3→5만 검증). 모델은 tiny로 다운로드 최소화 옵션 제공.

- [ ] 녹음→청크 전사→정지→저장 호출 경로를 end-to-end로 배선한다
  - task_id: T-013
  - owner_role: frontend_dev
  - phase: integrate
  - depends_on: [T-007, T-008, T-012]
  - acceptance:
    - 시작 → 캡처 스레드 2개 기동 → MixBuffer 청킹 → 워커 전사 → 정지 시 큐 drain → WAV + 전사 저장의 호출 체인이 코드상 연결된다(verification_focus #4).
    - Phase 4 finalization에서 캡처 스레드 join·잔여 버퍼 flush·큐 drain 타임아웃 가드가 동작한다(design §Event Sequence Phase 4).
    - 다음 작업자가 이어받을 handoff 메모(연결된 경로·잔여 리스크)가 기록된다(task board verify 단계 요구).
  - e2e_command: `pytest tests/test_integration_flow.py -q`
  - artifacts: tests/test_integration_flow.py, docs/handoff_notes.md
  - estimated_complexity: high
  - implementation_hint: mock 캡처 스트림으로 체인을 검증하되 최소 1개 실제 실행 경로(STT 1회) 포함 — stub-only PASS 금지.

- [ ] 헤드리스 검증 묶음(import·enumerate·셀프테스트·폴백)을 실행한다
  - task_id: T-014
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-013]
  - acceptance:
    - 모든 `app/*` 모듈 import가 비-Windows 포함 무오류로 통과한다(verification_focus #1).
    - `enumerate_devices()` 가 빈 목록 환경에서 예외 없이 안전 반환한다(verification_focus #2).
    - `python scripts/selftest.py` 가 exit 0이며 CUDA 미감지 시 CPU int8 폴백이 검증된다(verification_focus #3,#5).
    - 저장 경로에 절대경로 리터럴이 0건임이 코딩 컨벤션 테스트로 확인된다(verification_focus #6).
  - e2e_command: `python scripts/selftest.py && pytest tests/test_import_enumerate.py tests/test_no_hardcoded_path.py -q`
  - artifacts: tests/test_import_enumerate.py, tests/test_no_hardcoded_path.py
  - estimated_complexity: medium
  - implementation_hint: 장치 없는 환경은 PyAudio enumerate를 모킹. 절대경로 검사는 `C:\`, `/Users/`, `/home/`, `/root/` 리터럴 grep.

- [ ] 단위·통합·패키징 smoke를 종합 검증하고 잔여 리스크를 마감한다
  - task_id: T-015
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-010, T-014]
  - acceptance:
    - MixBuffer·detect_device·persistence 단위 테스트와 호출 경로 통합 테스트가 전부 통과한다(design §Test Strategy 3,4).
    - `python build.py` onedir 산출물에서 셀프테스트 smoke 실행이 성공하고 ctranslate2/onnxruntime DLL 동봉이 확인된다(design §Test Strategy 5).
    - 잔여 리스크(모델 다운로드, loopback 장치 의존, 드리프트)와 후속 작업이 문서로 기록된다(task board verify 요구).
  - e2e_command: `pytest -q && python build.py`
  - artifacts: docs/verification_report.md
  - estimated_complexity: medium
  - implementation_hint: 빌드 산출물 smoke는 `dist/.../meeting_stt_app --selftest` 1회. 리스크 표는 design §Risks 7항목을 상태와 함께 갱신.

---

## Blockers

- **모델 다운로드 의존**: faster-whisper 모델 미캐시 시 T-005/T-012가 네트워크에 의존. 오프라인 CI에서는 tiny 모델 사전 배치 또는 `HF_HOME` 캐시 필요.
- **WASAPI 플랫폼 종속**: T-003은 Windows 전용 — 비-Windows 검증은 import·STT 경로(T-012/T-014)로 한정된다.
- **네이티브 DLL 번들 리스크**: T-010 onedir 패키징에서 ctranslate2/onnxruntime DLL 누락 시 실행 실패. `binaries`/`datas` 명시가 선결 조건.
- **헤드리스 장치 부재**: 오디오 장치 0개 환경에서 enumerate 빈 목록 안전 처리가 보장되지 않으면 T-014가 BLOCK된다.

---

## Rollback Sign-Off

- 그린필드 프로젝트로 데이터 마이그레이션·기존 인터페이스 파괴가 없어, 롤백은 생성 산출물 제거로 환원된다(design §Migration Requirement).
- 각 build 태스크는 독립 파일 단위라 부분 롤백이 가능하다 — 문제 모듈만 직전 커밋으로 되돌리고 의존 태스크를 재실행한다.
- 패키징 산출물(`dist/`)은 빌드 캐시이므로 롤백 시 재생성 대상이며 git 추적 제외(`.gitignore`)를 유지한다.
- 롤백 판단 기준: T-014/T-015 e2e exit≠0 이 2회 연속 재현되면 해당 phase를 직전 PASS 지점으로 되돌리고 원인 태스크를 재오픈한다.

---

## Definition Of Done

- verification_focus 7항목이 모두 검증 가능한 e2e로 PASS한다(T-014, T-015).
- `python scripts/selftest.py` 가 합성 WAV로 STT 1회 통과해 `TranscriptChunk` 를 반환하고 exit 0이다.
- 녹음 시작→청크 전사→정지→WAV+전사 저장 호출 경로가 코드상 end-to-end 연결되고 통합 테스트가 통과한다(T-013).
- 저장 경로에 절대경로 리터럴이 0건이며 `meetings/` 하위로 해석된다.
- CUDA 미감지 시 CPU int8 폴백이 동작한다.
- `requirements.txt`, `README.md`, `build.spec`/`build.py` 가 존재하고 PyInstaller onedir 절차가 문서화되며 `dist/` 산출물 smoke가 성공한다.
- approval-gate `status=completed` 조건(파일 존재 + 금지토큰 0 + e2e exit 0)을 전 태스크가 충족한다.
- 잔여 리스크와 후속 작업이 `docs/verification_report.md` 에 기록되어 다음 작업자가 이어받을 수 있다.