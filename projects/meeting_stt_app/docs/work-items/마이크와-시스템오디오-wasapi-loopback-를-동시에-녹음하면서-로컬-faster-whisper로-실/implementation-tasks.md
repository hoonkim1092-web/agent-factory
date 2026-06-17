# Implementation Tasks

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실 |
| source_design | Implementation Design (Draft, 2026-06-13) · role-plan.json · task-board.json |
| status | Draft — 승인 대기 |
| last_updated | 2026-06-13 |

> 모든 명령어는 작업 루트 `D:\warkSpaces\agent-factory\projects\meeting_stt_app` 에서 실행하며, GUI 검증은 헤드리스를 위해 `QT_QPA_PLATFORM=offscreen` 환경에서 구동한다. STT 검증은 실장치 없이 합성 WAV 경로(`tests/selftest_synthetic.py`)로만 게이트한다.

---

## Preconditions

- Python 3.11 가상환경이 구성되어 있고 `pip` 사용 가능(faster-whisper/ctranslate2 wheel 호환 기준).
- 패키지 디렉터리 골격(`app/`, `app/audio/`, `app/stt/`, `app/ui/`, `app/persistence/`, `tests/`, `packaging/`)이 존재하거나 scope 단계에서 생성된다. 각 패키지에는 `__init__.py` 를 둔다.
- 비-Windows CI에서는 `pyaudiowpatch` import가 실패할 수 있으므로 캡처 모듈(`app/audio/capture.py`)은 **lazy import**로 격리하여 셀프테스트(STT 경로)가 보호되어야 한다.
- 모델 가중치는 최초 실행 시 다운로드되거나 onedir 빌드에 동봉. 헤드리스 검증은 `tiny` 모델 기본 사용(처리량 확보).
- 절대경로 하드코딩 금지(CLAUDE.md): 저장 경로는 앱 실행 폴더 하위 `meetings/<session_id>/` 상대 경로 또는 `Path.home()` 기반.

---

## Task Evidence

| 근거 | 출처 | 반영 태스크 |
|------|------|------------|
| FR-4 VAD 청크 스트리밍(롤링 버퍼 + `vad_filter` 또는 10~15초, 기본 `ko`/`auto`) | feature-spec §4 | T-002/T-012/T-013/T-022/T-023 |
| FR-5 STT 엔진(CUDA→float16, CPU→int8, 기본 `small`) | feature-spec §4 | T-001/T-011/T-013/T-021 |
| FR-6 UI(시작/정지·장치 드롭다운·모델·언어·자막 패널·타이머·레벨 미터·저장 경로) | feature-spec §4 | T-005/T-015/T-025 |
| FR-7 영속화(정지 시 `meetings/<session>/...wav` + 전사 `.txt`/`.md`) | feature-spec §4·§6 | T-004/T-014/T-024 |
| 비블로킹 워커 큐 + backpressure | Design Data Flow / R3 | T-013/T-015/T-016/T-026 |
| 헤드리스 합성 오디오 셀프테스트(장치 비의존) | Design Phase 5 / verification_focus #3 | T-010/T-020/T-023/T-030 |
| onedir 패키징(ctranslate2 DLL·모델 포함) | Design Alt #4 / R4 | T-008/T-018/T-028 |
| 경로 위생(절대경로 0) | CLAUDE.md / verification_focus #5 | T-014/T-024 |

---

## Task List

### Scope (계약·인터페이스 정의)

- [ ] **장치 enumerate·CUDA/CPU 자동감지 레이어 계약 정의**
  - task_id: T-001
  - owner_role: backend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `devices.enumerate() -> list[DeviceInfo]`, `device_detect.probe() -> DeviceProfile{device, compute_type, available}` 시그니처가 고정된다(spec §4 FR-5).
    - 장치 0개에서도 예외 없이 빈 목록을 반환하는 계약이 명시된다(R6).
  - e2e_command: `python -c "import app.audio.devices as d, app.stt.device_detect as p; assert hasattr(d,'enumerate') and hasattr(p,'probe')"`
  - artifacts: `app/audio/devices.py`, `app/stt/device_detect.py`
  - estimated_complexity: low
  - implementation_hint: probe는 `try: import torch; torch.cuda.is_available()` 또는 ctranslate2 가용성으로 분기, 실패 시 `compute_type="int8"` 디폴트.

- [ ] **마이크+시스템오디오 캡처·믹싱 엔진 인터페이스 정의**
  - task_id: T-002
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `AudioCapture.start(cfg: AudioDeviceConfig)` / `Mixer.read_chunk() -> np.ndarray | None` 계약이 고정된다.
    - 16kHz mono 믹스 스트림과 고품질 원본 PCM 두 갈래 분기가 설계에 명시된다(Design Data Flow).
  - e2e_command: `python -c "import app.audio.capture, app.audio.mixer"`
  - artifacts: `app/audio/capture.py`, `app/audio/mixer.py`
  - estimated_complexity: medium
  - implementation_hint: 캡처 스레드 A(mic)/B(loopback) 분리, `queue.Queue[np.ndarray]` 경계. capture는 lazy import로 pyaudiowpatch 격리.

- [ ] **faster-whisper 전사 워커·엔진 인터페이스 정의**
  - task_id: T-003
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `STTWorker.submit(chunk)`, `STTWorker.chunk_ready: Signal(TranscriptChunk)`, `engine.transcribe(...)` 시그니처가 고정된다(spec §4 FR-4/FR-5).
    - TranscriptChunk 필드(chunk_index/start_time/end_time/text/language/avg_logprob)가 계약으로 동결된다.
  - e2e_command: `python -c "import app.stt.engine, app.stt.worker"`
  - artifacts: `app/stt/engine.py`, `app/stt/worker.py`
  - estimated_complexity: medium
  - implementation_hint: 워커 1스레드 + `queue.Queue(maxsize=N)` backpressure. `transcribe(language=..., vad_filter=True)`.

- [ ] **세션 영속화 모듈 인터페이스 정의**
  - task_id: T-004
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `SessionStore.save(session, chunks, wav_pcm)` 계약과 산출물 4종(audio.wav/transcript.txt/transcript.md/session.json)이 명시된다(spec §6).
    - RecordingSession 필드가 계약으로 동결되고 경로는 상대 경로 규약으로 고정된다.
  - e2e_command: `python -c "import app.persistence.session_store as s; assert hasattr(s,'SessionStore')"`
  - artifacts: `app/persistence/session_store.py`
  - estimated_complexity: low
  - implementation_hint: `meetings/<session_id>/` 생성에 절대경로 리터럴 금지. session_id는 `YYYYMMDD_HHMMSS`.

- [ ] **UI 레이어(자막 패널·장치 드롭다운·레벨 미터) 인터페이스 정의**
  - task_id: T-005
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - MainWindow가 노출할 위젯(시작/정지·장치 2종·모델·언어·자막 패널·타이머·레벨 미터·저장 경로)이 명시된다(spec §4 FR-6).
    - STT 결과 수신은 `Signal(TranscriptChunk)` 슬롯 연결로만 처리한다는 비블로킹 계약이 고정된다.
  - e2e_command: `python -c "import app.ui.main_window, app.ui.widgets"`
  - artifacts: `app/ui/main_window.py`, `app/ui/widgets.py`
  - estimated_complexity: medium
  - implementation_hint: 모든 STT 호출은 워커 스레드, UI 슬롯은 append/갱신만.

- [ ] **앱 셸·생명주기·와이어링 범위 정의**
  - task_id: T-006
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - `app/main.py` 진입점이 모듈 2/3/4/5/10을 어떤 순서로 와이어링·기동/종료하는지 고정된다.
    - RecordingSession 상태머신(IDLE→RECORDING→STOPPING→SAVING→IDLE)이 명시된다(Design State Machine).
  - e2e_command: `python -c "import importlib.util as u; assert u.find_spec('app.main')"`
  - artifacts: `app/main.py`
  - estimated_complexity: low
  - implementation_hint: GPU 로드 실패 시 RECORDING 유지 + CPU fallback 분기 명시.

- [ ] **requirements.txt 의존성 명세 범위 정의**
  - task_id: T-007
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - faster-whisper/pyaudiowpatch/PySide6/numpy/soundfile/scipy 등 필수 의존성과 고정 버전 정책이 명시된다.
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('requirements.txt').exists() else 1)"`
  - artifacts: `requirements.txt`
  - estimated_complexity: low
  - implementation_hint: ctranslate2는 faster-whisper 전이 의존이지만 버전 핀 권장(R4 DLL 경로 변동 대비).

- [ ] **PyInstaller onedir 스펙·빌드 스크립트 범위 정의**
  - task_id: T-008
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - onedir 채택과 `binaries`/`datas`에 ctranslate2 DLL·모델 포함 정책이 명시된다(Design Alt #4, R4).
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('packaging/meeting_stt.spec').exists() else 1)"`
  - artifacts: `packaging/meeting_stt.spec`, `build.py`
  - estimated_complexity: medium
  - implementation_hint: onefile 금지(기동 지연·대용량 모델 동봉 불리).

- [ ] **README(설치·실행·시스템오디오 주의) 범위 정의**
  - task_id: T-009
  - owner_role: frontend_dev
  - phase: scope
  - depends_on: []
  - acceptance:
    - 설치/실행/사용법·WASAPI loopback 캡처 주의사항·헤드리스 셀프테스트 절차의 목차가 고정된다.
  - e2e_command: `python -c "import pathlib,sys; sys.exit(0 if pathlib.Path('README.md').exists() else 1)"`
  - artifacts: `README.md`
  - estimated_complexity: low
  - implementation_hint: 시스템오디오 미캡처(R1) 시 마이크 단독 fallback 안내 포함.

- [ ] **합성 오디오 헤드리스 셀프테스트 범위 정의**
  - task_id: T-010
  - owner_role: qa_engineer
  - phase: scope
  - depends_on: []
  - acceptance:
    - `run_selftest(wav_path | None) -> bool` 계약이 고정되고, 장치 enumerate 우회·STT 엔진 직접 주입 경로가 명시된다(Design Phase 5).
  - e2e_command: `python -c "import importlib.util as u; assert u.find_spec('tests.selftest_synthetic')"`
  - artifacts: `tests/selftest_synthetic.py`
  - estimated_complexity: low
  - implementation_hint: 440Hz 사인파 또는 샘플 WAV 생성 → `engine.transcribe()` 1회. exit code 0/1.

### Build (구현)

- [ ] **장치 enumerate·CUDA/CPU 자동감지 구현**
  - task_id: T-011
  - owner_role: backend_dev
  - phase: build
  - depends_on: [T-001]
  - acceptance:
    - `enumerate()`가 마이크·loopback 후보를 반환하고 장치 0개에서도 예외 없이 빈 목록을 반환한다(spec §4 FR-5, R6).
    - `probe()`가 CUDA 가용 시 `cuda/float16`, 아니면 `cpu/int8` 프로파일을 반환한다.
  - e2e_command: `python -c "import app.audio.devices as d, app.stt.device_detect as p; print(d.enumerate()); print(p.probe())"`
  - artifacts: `app/audio/devices.py`, `app/stt/device_detect.py`
  - estimated_complexity: medium
  - implementation_hint: pyaudiowpatch는 lazy import, 미설치/비-Windows에서 빈 목록 반환으로 graceful degrade.

- [ ] **캡처·리샘플·믹싱 오디오 엔진 구현**
  - task_id: T-012
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-002, T-011]
  - acceptance:
    - 마이크/loopback 두 스레드 입력을 16kHz mono로 리샘플·믹싱하고 `mix_gain`을 적용한다(spec §4 FR-4, R2).
    - 실시간 16kHz 믹스와 영속화용 고품질 원본 PCM 두 갈래가 동시에 흐른다(Design Data Flow).
  - e2e_command: `pytest tests/test_mixer.py -q`
  - artifacts: `app/audio/capture.py`, `app/audio/mixer.py`, `tests/test_mixer.py`
  - estimated_complexity: high
  - implementation_hint: scipy.signal.resample/resample_poly로 리샘플, 버퍼 큐 길이 보정으로 드리프트 완화.

- [ ] **faster-whisper 전사 워커·엔진 구현**
  - task_id: T-013
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-003, T-011]
  - acceptance:
    - 청크 dequeue → `transcribe(language="ko"|"auto", vad_filter=True)` → `TranscriptChunk` emit이 동작한다(spec §4 FR-4/FR-5).
    - 큐 `maxsize` 초과 시 backpressure(가장 오래된 청크 드롭)로 UI 비블로킹을 보장한다(R3).
  - e2e_command: `pytest tests/test_stt_engine.py -q`
  - artifacts: `app/stt/engine.py`, `app/stt/worker.py`, `tests/test_stt_engine.py`
  - estimated_complexity: high
  - implementation_hint: 모델 lazy 로드, GPU 로드 실패 시 try/except로 CPU int8 fallback(R5). 테스트는 `tiny`.

- [ ] **세션 영속화(WAV/.txt/.md/.json) 구현**
  - task_id: T-014
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-004]
  - acceptance:
    - `SessionStore.save()`가 `meetings/<session>/`에 audio.wav·transcript.txt·transcript.md·session.json 4종을 생성한다(spec §4 FR-7, §6).
    - 저장 경로 로직에 절대경로 리터럴(`C:\`, `/Users/`, `/home/`)이 없다(CLAUDE.md).
  - e2e_command: `pytest tests/test_session_store.py -q`
  - artifacts: `app/persistence/session_store.py`, `tests/test_session_store.py`
  - estimated_complexity: medium
  - implementation_hint: RecordingSession/TranscriptChunk JSON round-trip 검증 포함. soundfile로 WAV write.

- [ ] **UI 레이어(자막 패널·드롭다운·레벨 미터·타이머) 구현**
  - task_id: T-015
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-005, T-011, T-012, T-013]
  - acceptance:
    - 장치 드롭다운이 `enumerate()` 결과로 채워지고, `chunk_ready` 시그널 슬롯이 자막 패널에 append한다(spec §4 FR-6).
    - 타이머·레벨 미터·저장 경로 표시가 메인 스레드에서 갱신되며 STT 호출이 UI를 블로킹하지 않는다.
  - e2e_command: `QT_QPA_PLATFORM=offscreen python -c "import os; from app.ui.main_window import MainWindow; print('ui ok')"`
  - artifacts: `app/ui/main_window.py`, `app/ui/widgets.py`
  - estimated_complexity: high
  - implementation_hint: 드롭다운 빈 목록 시 "장치 없음" 비활성 상태 진입(R6).

- [ ] **앱 셸·상태머신·전체 와이어링 구현 (통합 지점)**
  - task_id: T-016
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-006, T-012, T-013, T-014, T-015]
  - acceptance:
    - 시작→캡처→청크 전사→정지→드레인→저장의 IDLE→RECORDING→STOPPING→SAVING→IDLE 흐름이 코드상 end-to-end 연결된다(Design State Machine, verification_focus #4).
    - GPU 로드 실패 시 CPU fallback으로 RECORDING이 유지된다(R5).
  - e2e_command: `QT_QPA_PLATFORM=offscreen python -c "import app.main; print('boot ok')"`
  - artifacts: `app/main.py`
  - estimated_complexity: high
  - implementation_hint: 정지 시 캡처 stop→버퍼 flush→큐 드레인→writer close 순서 보장.

- [ ] **requirements.txt 작성**
  - task_id: T-017
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-007]
  - acceptance:
    - 필수 의존성이 명시되고 `pip` dry-run 해석이 성공한다.
  - e2e_command: `python -m pip install -r requirements.txt --dry-run`
  - artifacts: `requirements.txt`
  - estimated_complexity: low
  - implementation_hint: PySide6/faster-whisper/pyaudiowpatch/numpy/soundfile/scipy/pyinstaller.

- [ ] **PyInstaller onedir 스펙·빌드 스크립트 구현**
  - task_id: T-018
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-008, T-016, T-017]
  - acceptance:
    - spec의 `binaries`/`datas`에 ctranslate2 DLL·모델 동봉 항목이 포함된다(R4).
    - `build.py`가 onedir 빌드를 호출하도록 구현된다.
  - e2e_command: `python -c "import pathlib; s=pathlib.Path('packaging/meeting_stt.spec').read_text(encoding='utf-8'); assert 'ctranslate2' in s and ('binaries' in s or 'datas' in s)"`
  - artifacts: `packaging/meeting_stt.spec`, `build.py`
  - estimated_complexity: medium
  - implementation_hint: collect_dynamic_libs('ctranslate2'), 모델 디렉터리 datas 추가.

- [ ] **README 작성**
  - task_id: T-019
  - owner_role: frontend_dev
  - phase: build
  - depends_on: [T-009, T-016]
  - acceptance:
    - 설치/실행/셀프테스트/패키징 절차와 WASAPI loopback·`meetings/` 경로 주의가 문서화된다(spec §6).
  - e2e_command: `python -c "import pathlib; t=pathlib.Path('README.md').read_text(encoding='utf-8'); assert 'meetings/' in t and 'WASAPI' in t"`
  - artifacts: `README.md`
  - estimated_complexity: low
  - implementation_hint: onedir 빌드 후 dist 스모크 절차 포함(R4).

- [ ] **합성 오디오 셀프테스트 스크립트 구현**
  - task_id: T-020
  - owner_role: qa_engineer
  - phase: build
  - depends_on: [T-010, T-013, T-014]
  - acceptance:
    - 합성 사인파/샘플 WAV를 STT 엔진에 직접 주입해 전사 텍스트(segment ≥1 또는 비어있지 않음)를 반환하고 exit code 0/1을 낸다(Design Phase 5, verification_focus #3).
    - 장치 enumerate를 우회하여 마이크 없는 환경에서도 통과한다(R6).
  - e2e_command: `python tests/selftest_synthetic.py`
  - artifacts: `tests/selftest_synthetic.py`
  - estimated_complexity: medium
  - implementation_hint: capture 모듈 import 회피 또는 lazy 격리로 비-Windows 보호.

### Verify (검증·핸드오프)

- [ ] **장치 레이어 검증·handoff**
  - task_id: T-021
  - owner_role: backend_dev
  - phase: verify
  - depends_on: [T-011]
  - acceptance:
    - `enumerate()`가 장치 0개에서 예외 없이 빈 목록을 반환함이 테스트로 확인된다(spec §7, R6).
    - probe의 CUDA/CPU 분기와 잔여 리스크(가상 드라이버 미탐지)가 handoff 메모에 기록된다.
  - e2e_command: `pytest tests/test_devices.py -q`
  - artifacts: `tests/test_devices.py`
  - estimated_complexity: low
  - implementation_hint: monkeypatch로 pyaudiowpatch 부재 시뮬레이션.

- [ ] **오디오 엔진 검증·handoff**
  - task_id: T-022
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-012]
  - acceptance:
    - Mixer 출력이 16kHz mono(샘플레이트·채널 단언)임이 확인된다(spec §4 FR-4).
    - 장시간 드리프트(R2) 잔여 위험과 주기적 리싱크 필요가 handoff에 기록된다.
  - e2e_command: `pytest tests/test_mixer.py tests/test_capture.py -q`
  - artifacts: `tests/test_capture.py`
  - estimated_complexity: medium
  - implementation_hint: 합성 2채널 스트림 주입으로 믹싱 정규화 검증.

- [ ] **STT 워커 검증·handoff**
  - task_id: T-023
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-013]
  - acceptance:
    - 합성 WAV가 파이프라인을 1회 통과해 전사 텍스트를 반환한다(verification_focus #3).
    - 큐 backpressure 드롭 동작과 저사양 CPU에서 medium 실시간 불가(R3)가 handoff에 기록된다.
  - e2e_command: `python tests/selftest_synthetic.py`
  - artifacts: `tests/test_stt_engine.py`
  - estimated_complexity: medium
  - implementation_hint: maxsize 초과 enqueue가 블로킹 없이 드롭됨을 단언.

- [ ] **영속화·경로 위생 검증·handoff**
  - task_id: T-024
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-014]
  - acceptance:
    - 더미 청크/PCM으로 4종 산출물이 `meetings/<session>/`에 생성되고 JSON round-trip이 일치한다(spec §4 FR-7).
    - 저장 경로에 절대경로 리터럴이 없음이 정적/단위 테스트로 확인된다(verification_focus #5).
  - e2e_command: `pytest tests/test_session_store.py tests/test_path_hygiene.py -q`
  - artifacts: `tests/test_path_hygiene.py`
  - estimated_complexity: medium
  - implementation_hint: tmp_path 픽스처 사용, grep 기반 절대경로 부재 검사.

- [ ] **UI 검증·handoff**
  - task_id: T-025
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-015]
  - acceptance:
    - 헤드리스(offscreen)에서 MainWindow 생성과 장치 드롭다운 채움이 예외 없이 동작한다(spec §4 FR-6).
    - 자막 패널 append가 시그널 슬롯 경유임이 코드로 확인되고 잔여 위험이 handoff에 기록된다.
  - e2e_command: `QT_QPA_PLATFORM=offscreen python -c "from app.ui.main_window import MainWindow; w=MainWindow(); print('ui verify ok')"`
  - artifacts: `app/ui/main_window.py`
  - estimated_complexity: medium
  - implementation_hint: 실제 자막 렌더·레벨 미터 시각 검증은 실장치 수동 체크리스트로 위임.

- [ ] **end-to-end 통합 검증·handoff (통합 게이트)**
  - task_id: T-026
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-016, T-020]
  - acceptance:
    - 합성 캡처 스트림으로 RECORDING→STOPPING→SAVING이 헤드리스 구동되어 WAV+전사 파일이 저장됨이 확인된다(verification_focus #4).
    - 앱 import 무오류 기동(`import app.main`)이 확인된다(verification_focus #1).
  - e2e_command: `QT_QPA_PLATFORM=offscreen python tests/selftest_synthetic.py --e2e`
  - artifacts: `tests/test_e2e_pipeline.py`
  - estimated_complexity: high
  - implementation_hint: UI 없이 파이프라인 체인만 구동하는 `--e2e` 경로 추가, 저장 파일 4종 존재 단언.

- [ ] **의존성 명세 검증·handoff**
  - task_id: T-027
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-017]
  - acceptance:
    - requirements 해석이 성공하고 핵심 패키지 import가 가능함이 확인된다.
  - e2e_command: `python -m pip install -r requirements.txt --dry-run`
  - artifacts: `requirements.txt`
  - estimated_complexity: low
  - implementation_hint: 버전 충돌 발생 시 핀 조정 후 재해석.

- [ ] **패키징 스펙 검증·handoff (수동/선택 CI)**
  - task_id: T-028
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-018]
  - acceptance:
    - onedir 빌드가 `dist/`에 산출물을 생성하고 ctranslate2 DLL·모델 포함이 확인된다(R4).
    - DLL 경로 변동 잔여 위험이 handoff에 기록된다.
  - e2e_command: `python build.py && python -c "import pathlib,sys; sys.exit(0 if any(pathlib.Path('dist').glob('**/meeting_stt*')) else 1)"`
  - artifacts: `packaging/meeting_stt.spec`, `build.py`
  - estimated_complexity: high
  - implementation_hint: 빌드 시간이 길어 CI에서는 선택 게이트, 스펙 정적 검사(T-018)를 1차 게이트로 사용.

- [ ] **README 검증·handoff**
  - task_id: T-029
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: [T-019]
  - acceptance:
    - 설치/실행/셀프테스트/패키징·시스템오디오 주의 항목이 모두 문서에 존재함이 확인된다(spec §6).
  - e2e_command: `python -c "import pathlib; t=pathlib.Path('README.md').read_text(encoding='utf-8'); assert all(k in t for k in ['meetings/','WASAPI','selftest','pyinstaller','requirements'])"`
  - artifacts: `README.md`
  - estimated_complexity: low
  - implementation_hint: 셀프테스트 실행 예시 명령을 README에 그대로 게재.

- [ ] **셀프테스트 게이트 검증·최종 handoff**
  - task_id: T-030
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: [T-020, T-026]
  - acceptance:
    - 셀프테스트가 exit 0으로 통과하고 Success Metrics 5종(헤드리스 기동·e2e 연결·패키징 문서화·장치 비의존 셀프테스트·경로 위생)이 done으로 확인된다.
    - 잔여 리스크(R1~R6)와 후속 작업이 최종 handoff 메모에 기록된다.
  - e2e_command: `python tests/selftest_synthetic.py; echo "exit=$?"`
  - artifacts: `tests/selftest_synthetic.py`
  - estimated_complexity: low
  - implementation_hint: 1~4번 헤드리스 자동 검증(T-021~T-026) 전부 PASS를 work item 완료 조건으로 묶어 보고.

---

## Blockers

- **T-028 패키징 검증**: onedir 풀빌드는 시간·디스크 비용이 커 매 변경마다 게이트하기 부적합. 1차 게이트는 스펙 정적 검사(T-018), 풀빌드는 릴리즈 직전 수동 또는 선택 CI로 한정.
- **실장치 검증 부재**: 실제 마이크+시스템오디오 동시 캡처·loopback 선택·GPU 경로·CUDA fallback(R5)은 헤드리스로 게이트 불가 → Windows 수동 체크리스트로 별도 처리. CI는 합성 WAV 경로만 게이트.
- **모델 다운로드 의존**: 오프라인/방화벽 CI에서 최초 모델 fetch 실패 가능 → `tiny` 모델 캐시 사전 배치 또는 동봉 경로 우선 필요.
- **R1 가상 오디오 드라이버**: 일부 가상 드라이버는 loopback 후보에 안 보일 수 있음 → 마이크 단독 fallback으로 graceful degrade, README 명시.

---

## Rollback Sign-Off

- 그린필드 신규 앱으로 기존 시스템 상태 변경이 없으므로 롤백은 **신규 `app/`·`tests/`·`packaging/`·`requirements.txt`·`README.md`·`build.py` 제거**로 한정된다(데이터 마이그레이션·스키마 역변환 불필요).
- 롤백 트리거: T-026(e2e 통합) 또는 T-030(셀프테스트 게이트)이 PASS하지 못하고 원인이 라이브러리 통합 비호환으로 판명될 경우.
- 안전 절차: 파괴적 삭제 명령 대신 변경 커밋 단위 revert로 처리. 워크스페이스 기존 산출물(`.todo.md`, `project_board_state.json`, 기존 work-items 3건)은 별도 디렉터리이므로 롤백 영향 없음.
- Sign-off 책임: 통합 게이트(T-026)·셀프테스트 게이트(T-030) 통과 기록과 함께 QA Engineer가 최종 서명.

---

## Definition Of Done

1. **헤드리스 기동**: `import app.main` 및 전 모듈 import가 오류 0으로 성공(T-016/T-026, verification_focus #1).
2. **장치 enumerate 안전성**: 장치 0개 환경에서 예외 없이 빈 목록 반환(T-021, R6).
3. **합성 WAV STT 1회 통과**: 셀프테스트가 전사 텍스트 반환 + exit 0(T-020/T-023/T-030, verification_focus #3).
4. **end-to-end 코드 연결**: 녹음 시작→청크 전사→정지→WAV+전사 저장이 실제 호출 체인으로 연결(T-026, verification_focus #4).
5. **경로 위생**: 저장 경로 절대경로 하드코딩 0, `meetings/` 상대 경로 사용(T-024, verification_focus #5).
6. **패키징 문서화**: onedir 스펙에 ctranslate2 DLL·모델 포함 명시 + 빌드 절차 문서화(T-018/T-019/T-028, verification_focus #6).
7. **자동 검증 게이트**: T-021~T-026 자동 검증이 모두 PASS해야 work item을 완료로 간주(잔여 리스크·후속 작업은 handoff에 기록).