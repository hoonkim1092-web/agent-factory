# Implementation Design

## Metadata
- **work_item**: 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시
- **spec_type**: implementation-design
- **source_spec**: feature-plan.md (회의록 STT 데스크톱 앱)
- **status**: draft
- **last_updated**: 2026-06-13

## Design Summary

본 설계는 마이크 입력과 시스템 출력(WASAPI loopback)을 **동시에 캡처·믹싱**하면서 로컬 faster-whisper로 **실시간 한국어 자막**을 출력하고, 종료 시 원본 WAV·전사 텍스트(.txt/.md)·세션 메타데이터(JSON)를 자동 저장하는 PySide6 Windows 데스크톱 앱을 정의한다.

핵심 설계 원칙은 **계층 격리(layered isolation)** 와 **논블로킹 파이프라인**이다. 캡처(I/O 스레드) → 믹싱·버퍼링(오디오 엔진) → 전사(워커 스레드) → UI 갱신(메인 스레드)을 큐로 분리하여 어느 단계도 UI 이벤트 루프를 블로킹하지 않는다. 이는 `required_capabilities`의 `concurrent_dual_stream_audio_capture`, `nonblocking_worker_queue_transcription`, `vad_chunked_streaming_stt`를 직접 충족하는 구조다.

기술 선택 근거:
- **faster-whisper (CTranslate2)**: 오프라인·무료·프라이버시 충족. CUDA 감지 시 `device=cuda/compute_type=float16`, 미감지 시 CPU `int8`로 자동 폴백하여 GPU 유무에 무관하게 동작. 내장 `vad_filter`를 사용해 외부 `webrtcvad` 의존성을 제거(`research_notes` 반영).
- **pyaudiowpatch**: PyAudio 포크로 WASAPI loopback을 표준 PyAudio API로 지원 — 별도 네이티브 바인딩 없이 마이크·loopback 두 스트림을 동일 코드 경로로 캡처.
- **PySide6(Qt6)**: 데스크톱 GUI 표준. `QThread`/`Signal-Slot`이 스레드 간 안전한 UI 갱신 메커니즘을 제공해 워커 큐와 자연스럽게 결합.
- **numpy**: 16kHz mono 리샘플·믹싱·RMS 레벨 계산을 단일 의존성으로 처리.
- **PyInstaller onedir**: ctranslate2 DLL·모델 가중치를 `binaries`/`datas`로 명시 번들. onefile 대비 압축 해제 지연이 없고 native DLL 로딩이 안정적(`pyinstaller_onedir_bundling_with_native_dll`).

`skill_gap_hypotheses`가 비어 있으므로 신규 스킬 forge 없이 기존 스택(PySide6, faster-whisper, pyaudiowpatch, numpy, soundfile, PyInstaller)을 **reuse** 전제로 진행한다.

## Planned Modules

| 모듈 | 파일(제안) | 책임 | 의존 |
|------|-----------|------|------|
| M1 앱 셸 | `app/main.py`, `app/__init__.py` | 엔트리포인트, QApplication 부트스트랩, 설정 로드, MainWindow 기동 | M4, M11 |
| M2 오디오 엔진 | `app/audio/capture.py`, `app/audio/mixer.py` | 마이크·loopback 각각 캡처 스레드, 16kHz mono 리샘플, 믹싱, 롤링 버퍼, 원본 WAV writer 피드 | M11 |
| M3 전사 워커 | `app/stt/transcriber.py`, `app/stt/worker.py` | faster-whisper 모델 로드(CUDA/CPU 분기), 청크 큐 소비, VAD/최대길이 청킹, `TranscriptChunk` emit | — |
| M4 UI | `app/ui/main_window.py`, `app/ui/widgets.py` | 시작/정지 버튼, 장치/모델/언어 드롭다운, 자막 패널(append), 타이머, 레벨 미터, 저장 경로 표시 | M2, M3 |
| M5 저장 모듈 | `app/io/recorder.py`, `app/io/transcript_writer.py` | 원본 WAV 저장, 전사 `.txt`/`.md` 생성 | M2, M3 |
| M6 세션 메타 | `app/io/session.py` | `RecordingSession` dataclass + JSON 직렬화 | M5 |
| M7 의존성 명세 | `requirements.txt` | 런타임 의존성 고정 | — |
| M8 README | `README.md` | 설치/실행/시스템오디오 캡처 주의·모델 다운로드 안내 | 전체 |
| M9 패키징 | `build.py`, `meeting_stt.spec` | PyInstaller onedir 스펙, ctranslate2 DLL/모델 번들, 빌드 절차 | 전체 |
| M10 셀프테스트 | `tests/selftest_pipeline.py` | 합성 사인파/샘플 WAV → STT 1회 전사 성공, 장치 enumerate graceful 검증 | M2, M3, M5 |
| M11 장치/설정 레이어 | `app/audio/devices.py`, `app/config.py` | 장치 enumerate, `AppSettings` JSON 영속, 저장 루트(`meetings/`) 해석 | — |

> **타입 SSOT**: `RecordingSession`/`TranscriptChunk`/`AppSettings` 3개 dataclass는 각각 단일 파일에서만 선언하고 타 모듈은 import한다(`session.py`, `stt/types.py`, `config.py`). 동일 타입 재선언 금지.

## Data Flow

```
[마이크 장치] ──capture thread──┐
                                ├─→ [AudioMixer] ──16kHz mono──┬─→ [원본 WAV writer] (M5)
[기본 스피커 loopback] ─thread──┘    (numpy resample/mix)      │
                                                               └─→ [RollingBuffer]
                                                                        │ VAD 무음 or max_chunk_sec(10~15s)
                                                                        ▼
                                                              [chunk_queue] (thread-safe)
                                                                        │
                                                              [TranscribeWorker] (QThread)
                                                                  faster-whisper.transcribe(vad_filter)
                                                                        │ TranscriptChunk
                                                                        ▼ Signal(chunk_ready)
                                                              [MainWindow 자막 패널 append] (UI thread)
                                                                        │
                                                              [TranscriptWriter 누적] (M5)

정지 시: 캡처 종료 → 잔여 버퍼 flush 전사 → WAV close → .txt/.md flush → RecordingSession JSON 저장
저장 루트: AppSettings.save_root or (홈/문서 or 앱폴더)/meetings/<session_id>/
```

- **레벨 미터**: AudioMixer가 믹싱 직후 RMS를 계산해 별도 Signal로 UI에 throttle(예: 50ms) 전달 — 전사 경로와 독립.
- **타이머**: 캡처 시작 시각 기준 UI 메인 스레드의 `QTimer`가 경과 시간 갱신(오디오 경로 비의존).

## Event Sequence / Phase Flow

상태 머신: `IDLE → INITIALIZING → RECORDING → STOPPING → SAVED`(오류 시 `ERROR`).

### Phase 1 — IDLE (대기/초기화)
- **진입 조건**: 앱 기동, `QApplication` 생성 완료.
- **핵심 이벤트**: `AppSettings` JSON 로드(없으면 기본값) → `devices.enumerate()`로 마이크·loopback 장치 목록 조회 → 드롭다운 채움 → 기본 `small` 모델을 백그라운드에서 lazy 로드(UI 블로킹 금지) → 저장 루트 표시.
- **장치 부재 graceful**: enumerate가 0개를 반환해도 예외 없이 빈 드롭다운 + 안내 라벨. 헤드리스에서도 import·기동 성공.
- **전환 트리거**: 사용자가 장치/모델/언어 선택 후 [녹음 시작] 클릭 → INITIALIZING.

### Phase 2 — INITIALIZING (캡처/워커 기동)
- **진입 조건**: 시작 버튼 클릭, 유효 장치 선택됨.
- **핵심 이벤트**: 모델 로드 완료 보장(미완 시 로딩 대기 표시) → `session_id` 생성, 저장 디렉터리 `meetings/<session_id>/` 생성 → 마이크 캡처 스레드 + loopback 캡처 스레드 start → `AudioMixer` 활성 → `TranscribeWorker(QThread)` start, `chunk_queue` 구독 → 원본 WAV writer open.
- **실패 처리**: loopback 활성 스피커 부재 시 캡처 실패 → 사용자 경고 + 마이크 단독 녹음으로 degrade(또는 중단 선택) → 부분 실패는 ERROR가 아닌 경고로 처리.
- **전환 트리거**: 두 캡처 스트림 중 최소 1개 활성 + 워커 ready → RECORDING.

### Phase 3 — RECORDING (실시간 전사 루프)
- **진입 조건**: 캡처·믹싱·워커 모두 가동.
- **핵심 이벤트(반복)**:
  1. 캡처 스레드가 프레임을 믹서에 push → 16kHz mono 리샘플·믹싱 → RollingBuffer 누적 + 원본 WAV 기록 + RMS→레벨 미터 Signal.
  2. RollingBuffer가 **VAD 무음 경계** 또는 **max_chunk_sec(10~15초)** 도달 → 청크를 `chunk_queue`에 enqueue.
  3. `TranscribeWorker`가 큐에서 청크를 꺼내 `faster-whisper.transcribe(language=ko|auto, vad_filter=True)` → `TranscriptChunk` 생성 → `chunk_ready` Signal emit.
  4. 메인 스레드가 자막 패널에 append + `TranscriptWriter` 누적. `QTimer`가 경과 시간 갱신.
- **백로그 가드**: `chunk_queue` 길이가 임계 초과 시 UI 경고(모델 다운그레이드 권고) — 큐는 무한 적체 대신 모니터링.
- **전환 트리거**: 사용자 [정지] 클릭 → STOPPING.

### Phase 4 — STOPPING (종료/flush)
- **진입 조건**: 정지 요청 수신.
- **핵심 이벤트**: 캡처 스레드에 stop 신호 → 두 스트림 join → 믹서 잔여 버퍼를 마지막 청크로 flush하여 워커에 전달 → 워커가 잔여 큐 소진까지 전사 후 종료 → 원본 WAV close.
- **전환 트리거**: 큐 비고 + 워커 종료 → SAVED.

### Phase 5 — SAVED (영속화/표시)
- **진입 조건**: 모든 전사 완료, 캡처 종료.
- **핵심 이벤트**: `TranscriptWriter`가 `.txt`/`.md` flush → `RecordingSession`(경로·모델·언어·장치·duration) JSON 저장 → UI에 최종 저장 경로 표시 → 상태 IDLE 복귀(재녹음 가능).
- **전환 트리거**: 저장 완료 → IDLE. 단계 중 예외 발생 시 ERROR(부분 산출물 보존 + 오류 표시).

## Interface Impact

신규 외부 프로젝트(`projects/meeting_stt_app`) 내부 모듈로 기존 Agent Factory 코어 인터페이스에 영향 없음(`blast_radius: isolated`). 내부 계약(요지):

```python
# app/audio/mixer.py
class AudioMixer:
    def push_mic(self, frames: np.ndarray) -> None: ...
    def push_loopback(self, frames: np.ndarray) -> None: ...
    def read_chunk(self) -> Optional[np.ndarray]: ...   # VAD/max_len 도달 시 반환
    level_changed: Signal  # float RMS

# app/stt/transcriber.py
class Transcriber:
    def __init__(self, model_size: str, language: str): ...  # CUDA/CPU 자동 분기
    def transcribe_chunk(self, audio: np.ndarray) -> list[TranscriptChunk]: ...

# app/stt/worker.py (QThread)
class TranscribeWorker(QThread):
    chunk_ready: Signal  # TranscriptChunk
    def enqueue(self, audio: np.ndarray) -> None: ...
    def stop_and_drain(self) -> None: ...

# app/audio/devices.py
def enumerate_devices() -> tuple[list[Device], list[Device]]: ...  # (mics, loopbacks), 빈 리스트 허용
```

## State And Data Model

- **RecordingSession** (storage=json): `session_id, started_at, ended_at, wav_path, transcript_txt_path, transcript_md_path, model_size, language, mic_device, loopback_device, duration_sec` — 세션 종료 시 `meetings/<session_id>/session.json`에 저장.
- **TranscriptChunk** (storage=memory): `chunk_index, start_ts, end_ts, text, language, no_speech_prob` — 워커→UI 전달 단위. 영속화는 텍스트로 직렬화되어 `.txt`/`.md`에 누적.
- **AppSettings** (storage=json): `model_size, language, mic_device_index, loopback_device_index, save_root, max_chunk_sec, use_vad` — 앱 종료/변경 시 사용자 설정 디렉터리에 영속.

상태 머신: `IDLE/INITIALIZING/RECORDING/STOPPING/SAVED/ERROR`(Phase Flow 참조). 모든 상태 전환은 메인 스레드에서 단일 소유되어 race 제거.

## Compatibility Considerations

- **OS**: Windows 전용(WASAPI). macOS/Linux는 Non-Goal — `pyaudiowpatch`·loopback 경로는 import 가드로 감싸 비-Windows에서 명시적 미지원 메시지.
- **GPU 유무**: CUDA 감지 실패 시 CPU `int8` 자동 폴백 — 동일 코드 경로, 사용자 개입 불필요.
- **모델 부재/오프라인**: 최초 실행 모델 다운로드 지연 가능 → README에 사전 다운로드 안내 + 패키징 시 모델 번들 옵션. 오프라인에서 모델 부재 시 명시적 오류 안내.
- **헤드리스/CI**: 장치 enumerate·캡처 경로는 장치 0개에서도 예외 없이 진행. 셀프테스트는 장치 없이 합성 WAV로 전사 검증.

## Migration Requirement

기존 데이터·스키마 마이그레이션 없음(신규 앱). 워크스페이스의 기존 초안(`feature-spec/feature-plan/implementation-tasks/task_execution_plan`, `.todo.md`, `project_board_state.json`, work_item 2건)은 **재설계 대상이 아니라 구현 진입의 출발점**으로 이어받는다. `AppSettings`/`RecordingSession` JSON은 신규 생성이며 하위 호환 부담 없음.

## Risks

- **WASAPI loopback 캡처 실패**(활성 스피커 부재): INITIALIZING에서 감지 → 마이크 단독 degrade 또는 사용자 중단 선택. (`concurrent_dual_stream_audio_capture` 부분 충족 경로 명시)
- **믹싱 드리프트/싱크**: 마이크·loopback 샘플레이트·채널·타이밍 차이 → 공통 16kHz mono 리샘플 + 버퍼 정렬로 완화. 장기 녹음 드리프트는 버퍼 길이 정규화로 흡수.
- **전사 백로그**: CPU `int8` small이 실시간보다 느릴 때 `chunk_queue` 적체 → 큐 길이 모니터링 + 모델 다운그레이드 권고. (`nonblocking_worker_queue_transcription` 보강)
- **번들 누락**: ctranslate2 DLL·모델 가중치 PyInstaller 누락 → `.spec`에 `binaries`/`datas`/`hiddenimports` 명시 + 빌드 후 셀프테스트 1회 전사로 검증.
- **헤드리스 장치 부재**: enumerate/캡처 실패 → graceful 분기 + 합성 WAV 우회.
- **모델 다운로드 지연/오프라인 부재**: 사전 번들 또는 명시 안내.

## Alternatives Considered

- **sounddevice/soundcard vs pyaudiowpatch**: loopback을 표준 PyAudio 호출로 마이크와 **동일 코드 경로**로 처리할 수 있는 pyaudiowpatch 채택(아키텍처 제약·변경 금지). 두 스트림을 이종 API로 다루는 복잡도 회피.
- **외부 webrtcvad vs faster-whisper 내장 vad_filter**: 의존성 최소화·청킹 일관성을 위해 내장 `vad_filter` 채택(`research_notes`).
- **whisper.cpp / OpenAI API vs faster-whisper**: 클라우드 API는 프라이버시·비용·오프라인 제약으로 배제(Non-Goal). whisper.cpp 대비 CTranslate2 백엔드의 Python 통합·CUDA/CPU 자동 분기가 단순.
- **multiprocessing vs QThread 워커**: GUI와의 Signal-Slot 연동·공유 메모리 단순성으로 QThread 채택. GIL 영향은 전사가 CTranslate2 네이티브 연산(GIL 해제)에서 수행되어 실질 병행 확보.
- **PyInstaller onefile vs onedir**: onefile은 native DLL 임시 추출 지연·로딩 이슈 → onedir 채택(아키텍처 제약).

## Design Evidence

### 검증 기준 (verification_focus)
- 모듈 import가 헤드리스에서 오류 없이 성공.
- 장치 enumerate가 장치 0개 환경에서도 graceful 동작.
- 합성 사인파/샘플 WAV가 faster-whisper 파이프라인을 **1회 전사 성공**(핵심 통과 조건).
- 녹음 시작 → 자막 append → 정지 → WAV+전사 저장이 코드상 **end-to-end 연결**.
- 전사 워커가 UI 스레드를 블로킹하지 않음(큐/스레드 분리 확인).
- 저장 경로에 절대경로 하드코딩 없음, `meetings/` 하위 생성.
- PyInstaller 빌드 스크립트 존재 + 패키징 절차 문서화.

### 스킬 조달 신호 (required_capabilities / skill_gap_hypotheses)
- 필요 역량(`concurrent_dual_stream_audio_capture`, `realtime_audio_resample_and_mix`, `nonblocking_worker_queue_transcription`, `vad_chunked_streaming_stt`, `wav_and_transcript_persistence`, `headless_synthetic_audio_selftest`, `pyinstaller_onedir_bundling_with_native_dll`)은 모두 확정 기술 스택 내에서 충족 가능.
- `skill_gap_hypotheses`가 비어 있어 신규 스킬 forge 신호 없음 → 기존 스킬 **reuse** 전제. enhance/forge 불필요.

## References

- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-spec.md` — Outputs/Feature Overview/Inputs (확정 산출물·아키텍처·입력)
- `docs/work-items/.../feature-plan.md` — Goals
- `docs/work-items/.../implementation-tasks.md` — Metadata (work_item / source_design)
- `docs/task_execution_plan.md` — Overview (role 4 · module 11 · task 33)
- 워크스페이스 산출물: `.todo.md`, `project_board_state.json`, work_item 2건

## Test Strategy

검증 우선순위는 **헤드리스 셀프테스트**(완료 기준의 핵심)다.

1. **import 스모크 테스트**: 전 모듈 import가 장치 없이 오류 없이 성공.
2. **장치 enumerate graceful 테스트**: `enumerate_devices()`가 장치 0개에서도 빈 리스트 반환·예외 없음.
3. **합성 오디오 STT 1회 전사**(`tests/selftest_pipeline.py`): 16kHz mono 합성 사인파/샘플 WAV를 `Transcriber.transcribe_chunk`에 통과시켜 `TranscriptChunk` ≥1 생성 확인 — 마이크 없는 CI에서 완료 기준 충족 경로.
4. **end-to-end 배선 테스트**: 합성 오디오 스트림을 AudioMixer→chunk_queue→Worker→TranscriptWriter→Recorder까지 흘려 WAV + `.txt`/`.md` + `session.json`이 `meetings/<session_id>/`에 생성되는지 확인.
5. **논블로킹 검증**: 워커 전사 중 메인 스레드 응답성(큐/스레드 분리) 단위 확인 — 전사 호출이 UI 슬롯에서 직접 실행되지 않음을 코드 경로로 검증.
6. **절대경로 하드코딩 부재**: 저장 경로 해석이 `Path.home()`/문서폴더/앱폴더 기반이며 `C:\`·`/Users/` 리터럴이 없음(정적 검사).
7. **패키징 검증**: `build.py`/`.spec` 존재 확인 + onedir 빌드 산출물에서 셀프테스트 1회 전사 재실행으로 ctranslate2 DLL·모델 번들 무결성 확인.