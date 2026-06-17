# Implementation Design

## Metadata

- **work_item**: 회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp
- **spec_type**: implementation-design
- **source_spec**: feature-plan.md (회의록 STT 데스크톱 앱)
- **status**: draft
- **last_updated**: 2026-06-13

---

## Design Summary

회의 음성을 **마이크 + 시스템오디오(WASAPI loopback)** 두 채널로 동시 캡처하여 16kHz mono로 믹싱하고, 로컬 **faster-whisper**로 실시간 한국어 자막을 출력하며, 종료 시 **WAV + 전사(.txt/.md)**를 자동 저장하는 **PySide6 Windows 데스크톱 앱**을 구현한다.

핵심 설계 원칙은 **3-스레드 + 큐 분리 아키텍처**다. UI 스레드(Qt 이벤트 루프)는 절대 블로킹되지 않으며, 오디오 캡처는 별도 스레드 2개(마이크/loopback), STT 추론은 워커 스레드 1개로 격리한다. 스레드 간 데이터는 `queue.Queue`로만 전달하고, 워커→UI 결과 반영은 Qt `Signal/Slot`(스레드-세이프)으로 마샬링한다.

기술 선택 근거:

| 선택 | 근거 |
|------|------|
| **로컬 faster-whisper** | 클라우드 STT의 프라이버시·비용·인터넷 의존 문제 제거. ctranslate2 백엔드로 동급 정확도 대비 CPU에서도 실용 속도. `vad_filter=True`로 내장 Silero VAD 활용 → 무음 청크 추론 비용 절감. |
| **pyaudiowpatch** | PyAudio 포크로 WASAPI loopback을 공식 지원(`get_default_wasapi_loopback()`). 시스템 출력(상대방 음성)을 별도 장비 없이 소프트웨어로 캡처하는 표준 경로. |
| **PySide6** | LGPL 라이선스로 상용 배포 자유. `QThread`/`Signal` 기반 비블로킹 GUI가 실시간 자막 append 요구에 부합. |
| **queue.Queue 분리** | 오디오 I/O(고빈도, 저지연)와 STT 추론(저빈도, 고지연)의 처리율 불일치를 구조적으로 흡수. GUI 스레드 블로킹을 컴파일 타임에 차단. |
| **PyInstaller onedir** | ctranslate2/onnxruntime 네이티브 DLL과 모델 파일을 함께 번들. onefile은 임시 추출 오버헤드·DLL 누락 위험이 커 onedir 채택. |

조달이 필요한 **required_capabilities**: `concurrent_dual_stream_audio_capture`, `wasapi_loopback_access`, `local_offline_stt_inference`, `non_blocking_gui_threading`, `audio_buffer_vad_chunking`, `wav_and_transcript_persistence`, `onedir_native_dll_packaging`, `headless_synthetic_audio_verification`. 이 중 오디오 캡처·STT·패키징은 외부 라이브러리(reuse), 믹싱/청킹/저장/셀프테스트는 자체 구현(forge) 신호로 분류한다.

---

## Planned Modules

프로젝트는 `app/` 패키지 구조로 구성하며, 각 모듈은 단일 책임을 갖고 인터페이스로만 결합한다.

| 모듈 | 파일 | 책임 | owner_role |
|------|------|------|-----------|
| **진입점** | `app/main.py` | QApplication 부트스트랩, MainWindow 생성, CLI 인자(`--selftest`) 분기 | frontend_dev |
| **설정/경로** | `app/config.py` | `AudioConfig`/`RecordingSession` dataclass, save_dir 해석(`meetings/`), CUDA 감지·디바이스 선택 | frontend_dev |
| **오디오 캡처 엔진** | `app/audio/capture.py` | 마이크·loopback 캡처 스레드 2개, 장치 enumerate, 16kHz mono 리샘플 | frontend_dev / backend_dev |
| **믹서/버퍼** | `app/audio/mixer.py` | 두 스트림 합산 믹싱, 롤링 버퍼 누적, VAD/최대길이 기반 청크 경계 산출 | designer(threading) / frontend_dev |
| **STT 워커** | `app/stt/worker.py` | faster-whisper 모델 로드, 청크 큐 소비, `transcribe(vad_filter=True, language)`, 결과 Signal emit | frontend_dev |
| **저장 모듈** | `app/persistence.py` | 원본 WAV 저장(soundfile), 전사 `.txt`/`.md` 직렬화, session JSON 기록 | frontend_dev |
| **메인 윈도우** | `app/ui/main_window.py` | 시작/정지 버튼, 장치·모델·언어 드롭다운, 타이머, 저장 경로 표시 | frontend_dev |
| **자막/레벨 위젯** | `app/ui/widgets.py` | 자막 패널(청크 append), 오디오 레벨 미터 | frontend_dev |
| **셀프테스트** | `scripts/selftest.py` | 합성 사인파→16kHz mono WAV→STT 1회 통과 검증(헤드리스) | qa_engineer |
| **의존성/패키징** | `requirements.txt`, `build.spec`, `build.py` | 의존성 명세, PyInstaller onedir 스펙·빌드 스크립트 | frontend_dev |
| **문서** | `README.md` | 설치/실행/시스템오디오 캡처 주의사항 | frontend_dev |

모듈 의존 방향(상위→하위, 단방향): `main → ui → {audio, stt, persistence} → config`. UI는 엔진을 호출하지만 엔진은 UI를 import하지 않으며, 결과 전달은 Signal로만 한다(헤드리스 셀프테스트가 UI 없이 엔진을 직접 구동 가능해야 하므로).

---

## Data Flow

```
[마이크 장치] ──mic_thread──┐
                            ├─► [MixBuffer(롤링)] ──청크경계 도달──► [chunk_queue]
[스피커 loopback] ─loop_thread─┘        │                                  │
                                        │                                  ▼
                                  (16kHz mono 리샘플·믹싱)          [STT 워커 스레드]
                                        │                          model.transcribe(
                                        ▼                            vad_filter=True,
                              [원본 WAV 누적 버퍼]                    language="ko")
                                        │                                  │
                                        ▼                                  ▼ (Qt Signal)
                              정지 시 ─► soundfile.write             [자막 패널 append]
                                        │                                  │
                                        ▼                                  ▼ 정지 시
                              meetings/<session>/audio.wav        meetings/<session>/transcript.{txt,md}
                                                                           │
                                                                           ▼
                                                                  session.json (메타데이터)
```

- **고빈도 경로**(캡처→믹싱): 콜백/스레드에서 매 버퍼(예: 100~200ms) 단위로 동작. 리샘플은 정수비(예: 48k→16k) 우선, 비정수비는 `scipy.signal.resample_poly` 사용.
- **저빈도 경로**(청크→STT): VAD 무음 감지 또는 최대 길이(10~15초, 설정값) 도달 시 1청크를 `chunk_queue.put()`. 워커는 blocking get으로 소비 → GUI와 완전 비동기.
- **결과 마샬링**: 워커는 UI 위젯을 직접 건드리지 않고 `transcribed = Signal(TranscriptChunk)`만 emit. Qt가 UI 스레드 컨텍스트로 자동 큐잉.

---

## Event Sequence / Phase Flow

시스템 전체 실행 흐름을 5개 Phase 상태머신으로 정의한다. 상태는 `AppState ∈ {IDLE, ENUMERATED, RECORDING, FINALIZING, SAVED}`.

### Phase 1 — Startup & Enumeration (IDLE → ENUMERATED)

- **진입 조건**: 앱 실행(`main.py`), QApplication 초기화 완료.
- **핵심 이벤트**:
  - CUDA 감지 → `device=cuda/compute_type=float16` 또는 폴백 `cpu/int8` 결정(`config.detect_device()`).
  - PyAudio host API 순회로 마이크 후보 + WASAPI loopback 후보 enumerate → 드롭다운 채움.
  - 장치 0개(헤드리스/CI)면 빈 목록을 **예외 없이** 안전 처리하고 시작 버튼 비활성화 + 안내 라벨 표시.
- **다음 Phase 전환 트리거**: 사용자가 모델 크기·언어·장치 선택 후 **녹음 시작** 클릭.

### Phase 2 — Recording & Capture (ENUMERATED → RECORDING)

- **진입 조건**: 시작 버튼 클릭, 유효 장치 선택됨.
- **핵심 이벤트**:
  - faster-whisper 모델 로드(첫 실행 시 다운로드 — 로딩 스피너/상태 표시). 로드는 워커 스레드 사전 워밍업으로 수행해 UI 비블로킹.
  - `mic_thread`, `loopback_thread` 기동 → 각자 16kHz mono 리샘플 후 `MixBuffer`에 push.
  - 녹음 타이머 시작, 레벨 미터 갱신(`QTimer` 폴링 또는 Signal).
  - 원본 WAV 누적 시작.
- **다음 Phase 전환 트리거**: (a) 청크 경계 도달 → Phase 3로 **부분 진입(병렬)**, (b) 사용자 **정지** 클릭 → Phase 4.

### Phase 3 — Realtime Chunk Transcription (RECORDING 내부 루프)

- **진입 조건**: `MixBuffer`가 VAD 무음 감지 또는 최대 길이(10~15초) 도달.
- **핵심 이벤트**:
  - 청크 슬라이스를 `chunk_queue.put()` (버퍼는 약간의 overlap을 남겨 단어 잘림 완화).
  - 워커가 `model.transcribe(chunk, vad_filter=True, language=cfg.language)` 실행.
  - 세그먼트별 `TranscriptChunk(chunk_index, start_ts, end_ts, text, language, avg_logprob)` 생성 → `transcribed` Signal emit.
  - 자막 패널에 청크 단위 append, 메모리 누적 리스트에도 보관.
- **다음 Phase 전환 트리거**: RECORDING 지속 중에는 이 루프 반복. 정지 신호 수신 시 Phase 4.

### Phase 4 — Finalization (RECORDING → FINALIZING)

- **진입 조건**: 사용자 정지 클릭.
- **핵심 이벤트**:
  - 캡처 스레드 2개에 정지 플래그 set → join.
  - `MixBuffer` 잔여분을 마지막 청크로 flush → 워커 큐에 투입 후 큐 drain 대기(타임아웃 가드 포함).
  - 누적 WAV를 `soundfile.write`로 `meetings/<session_id>/audio.wav` 저장.
- **다음 Phase 전환 트리거**: 큐 drain 완료 + WAV 쓰기 성공 → Phase 5.

### Phase 5 — Persistence & Display (FINALIZING → SAVED)

- **진입 조건**: 모든 청크 전사 완료, WAV 저장 완료.
- **핵심 이벤트**:
  - 전사 누적본을 `.txt`(플레인)와 `.md`(타임스탬프·세션 헤더 포함)로 직렬화 저장.
  - `RecordingSession` 메타데이터를 `session.json`에 기록.
  - UI에 최종 저장 경로 표시, 상태를 IDLE로 리셋 가능하게 함.
- **다음 Phase 전환 트리거**: 사용자가 새 녹음 시작 시 Phase 2로 회귀(모델 재로드 없이 재사용).

> **헤드리스 변형 흐름**: `scripts/selftest.py`는 Phase 1의 장치 enumerate를 건너뛰고, 합성 사인파 WAV를 직접 `chunk_queue`에 주입해 Phase 3→5만 검증한다(UI 없이 엔진 직접 구동).

---

## Interface Impact

신규 프로젝트이므로 기존 인터페이스 파괴는 없다. 모듈 간 핵심 계약은 다음과 같다.

```python
# app/config.py
@dataclass
class AudioConfig:
    mic_device_index: int | None
    loopback_device_index: int | None
    sample_rate: int = 16000
    channels: int = 1
    model_size: str = "small"      # tiny|base|small|medium
    language: str = "ko"           # ko|auto
    save_dir: Path                 # 기본: <app_root>/meetings 또는 ~/Documents/meetings

def detect_device() -> tuple[str, str]:   # ("cuda","float16") | ("cpu","int8")

# app/audio/capture.py
def enumerate_devices() -> tuple[list[DeviceInfo], list[DeviceInfo]]:  # (mics, loopbacks); 빈 목록 안전
class CaptureThread(threading.Thread):     # target_device, out_buffer, stop_event

# app/audio/mixer.py
class MixBuffer:
    def push(self, samples: np.ndarray, source: str) -> None
    def pop_chunk(self) -> np.ndarray | None    # VAD/maxlen 도달 시에만 반환

# app/stt/worker.py  (QObject)
class TranscribeWorker(QObject):
    transcribed = Signal(object)   # TranscriptChunk
    finished = Signal()
    def __init__(self, cfg: AudioConfig, chunk_queue: queue.Queue): ...

# app/persistence.py
def save_wav(buf: np.ndarray, path: Path, sample_rate: int) -> None
def save_transcript(chunks: list[TranscriptChunk], txt_path: Path, md_path: Path) -> None
def save_session(session: RecordingSession, path: Path) -> None
```

UI(`main_window.py`)는 위 계약만 의존하며, 워커의 `transcribed` Signal을 자막 패널 슬롯에 연결한다.

---

## State And Data Model

| Entity | 저장 | 필드 | 비고 |
|--------|------|------|------|
| **RecordingSession** | json (`session.json`) | session_id, start_time, end_time, wav_path, transcript_path, model_size, language, device | 세션 단위 메타데이터. session_id는 시작 시각 기반 슬러그. |
| **TranscriptChunk** | memory(런타임) | chunk_index, start_ts, end_ts, text, language, avg_logprob | 정지 시 일괄 직렬화. avg_logprob는 신뢰도 표시·후처리용. |
| **AudioConfig** | json (사용자 설정) | mic_device_index, loopback_device_index, sample_rate, channels, model_size, language, save_dir | 마지막 선택 장치/모델 기억(다음 실행 복원). |

**앱 상태머신**: `IDLE → ENUMERATED → RECORDING ⇄ (chunk loop) → FINALIZING → SAVED → (재시작 시) RECORDING`. 상태 전이는 UI 스레드에서만 변경하고, 워커/캡처 스레드는 stop_event·큐로만 통신한다.

**저장 경로 정책(절대경로 하드코딩 금지)**: `save_dir`는 우선순위로 ① 사용자 설정값 → ② `Path.home() / "Documents" / "meetings"` → ③ `Path(__file__).resolve().parent.parent / "meetings"` 순으로 해석. `C:\`, `/Users/`, `/home/` 등 리터럴 절대경로 사용 금지(코딩 컨벤션 준수).

---

## Compatibility Considerations

- **플랫폼**: Windows 전용(WASAPI loopback). macOS/Linux는 non-goal — 캡처 모듈 import 시 플랫폼 가드로 명확한 에러 메시지 반환(헤드리스 셀프테스트는 STT 경로만 검증하므로 비-Windows에서도 import는 통과하도록 캡처 import를 지연 로딩).
- **GPU/CPU**: CUDA/cuDNN 버전 불일치 시 GPU 로드 실패 → `try/except`로 CPU int8 자동 폴백. 폴백 발생 시 UI 상태 라벨에 명시.
- **Python**: 3.11 고정(ctranslate2/onnxruntime wheel 호환성).
- **모델 캐시**: 첫 실행 시 small(~500MB) 다운로드. 오프라인 환경은 `HF_HOME`/모델 경로 사전 배치 안내(README). 패키징 시 모델을 번들에 포함하는 옵션 제공.
- **샘플레이트 드리프트**: 두 스트림을 공통 16kHz 타임라인으로 리샘플하되, 길이 불일치 시 짧은 쪽을 zero-pad로 정렬해 믹싱 동기 어긋남 완화.

---

## Migration Requirement

신규 그린필드 프로젝트로 **데이터 마이그레이션 없음**. 기존 자산과의 연계 요구사항은 다음만 존재한다.

- 워크스페이스의 기존 work-item 문서 세트(feature-spec/implementation-design/task_execution_plan)는 인터페이스 정의의 baseline 참고용이며, 본 설계가 그 계약을 구체화한다.
- 향후 모델 캐시 위치·설정 스키마(`AudioConfig` json) 변경 시 하위호환을 위해 누락 필드는 기본값으로 채우는 방어적 로딩을 적용한다.

---

## Risks

| 리스크 | 영향 | 완화책 |
|--------|------|--------|
| WASAPI loopback이 기본 스피커 변경·장치 미존재 시 실패 | 시스템오디오 캡처 불가 | `get_default_wasapi_loopback()` 실패 시 명시적 에러 + 마이크 단독 모드 폴백. 장치 enumerate 빈 목록 안전 처리. |
| faster-whisper 모델 다운로드 지연·오프라인 캐시 부재 | 첫 실행 지연/실패 | 로딩 상태 표시, README에 오프라인 캐시 배치 절차. 패키징 시 모델 번들 옵션. |
| 두 스트림 샘플레이트·버퍼 드리프트 | 믹싱 동기 어긋남 | 공통 16kHz 리샘플 + 길이 정렬(zero-pad). 청크 overlap. |
| CUDA/cuDNN 버전 불일치 | GPU 경로 로드 실패 | CPU int8 자동 폴백 + 폴백 검증 셀프테스트. |
| PyInstaller가 ctranslate2/onnxruntime DLL·모델 누락 | 빌드 실행 실패 | `build.spec`에 `binaries`/`datas`로 네이티브 DLL·모델 명시. onedir 채택. 빌드 후 smoke 실행 검증. |
| 실시간 청크 경계 단어 잘림 | 전사 정확도 저하 | 청크 간 overlap(예: 0.5~1초) + VAD 무음 우선 경계로 자연 분절. |
| CI/헤드리스에 오디오 장치 없음 | enumerate 빈 목록 | enumerate가 빈 리스트 반환 시 예외 없이 처리, 셀프테스트는 합성 WAV로 STT만 검증. |

---

## Alternatives Considered

| 대안 | 기각 사유 |
|------|----------|
| **클라우드 STT(OpenAI Whisper API 등)** | 프라이버시·비용·인터넷 의존 — 확정 아키텍처에서 명시적 금지(non-goal). |
| **sounddevice/soundcard for loopback** | WASAPI loopback 지원이 불안정·플랫폼 의존. pyaudiowpatch가 공식 `get_default_wasapi_loopback()` 제공으로 더 안정. |
| **openai-whisper(원본)** | ctranslate2 백엔드 대비 CPU 추론 느림·메모리 큼. faster-whisper가 실시간 청크에 유리. |
| **Tkinter GUI** | Signal/Slot 기반 스레드-세이프 UI 갱신이 약함. PySide6가 비블로킹 자막 append에 적합. |
| **PyInstaller onefile** | 임시 추출 오버헤드·네이티브 DLL 누락 위험. onedir이 디버깅·DLL 동봉에 안정. |
| **단일 스레드 + 콜백 STT** | STT 추론(수백ms~수초)이 콜백 내에서 GUI 블로킹 유발. 큐+워커 분리가 구조적 해법. |

---

## Design Evidence

본 설계의 검증 기준은 brief의 **verification_focus**를 그대로 채택한다:

1. 모듈 import가 오류 없이 성공하는지(헤드리스) — 캡처 모듈 지연 로딩으로 비-Windows에서도 엔진 import 통과.
2. 오디오 장치 enumerate가 예외 없이 동작하고 빈 목록도 안전 처리하는지.
3. 합성 사인파 WAV가 faster-whisper STT 파이프라인을 1회 통과해 전사 결과를 반환하는지.
4. 녹음 시작→청크 전사→정지→WAV+전사 저장의 호출 경로가 코드상 end-to-end 연결되는지.
5. CUDA 미감지 시 CPU int8 경로로 폴백되는지.
6. 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위로 해석되는지.
7. PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있는지.

**스킬 조달 신호(reuse/enhance/forge)**:
- **reuse**: `wasapi_loopback_access`(pyaudiowpatch), `local_offline_stt_inference`(faster-whisper), `onedir_native_dll_packaging`(PyInstaller) — 검증된 외부 라이브러리 직접 활용.
- **enhance**: `non_blocking_gui_threading`(PySide6 Signal/Slot + queue 조합), `concurrent_dual_stream_audio_capture`(2-thread 패턴).
- **forge**: `audio_buffer_vad_chunking`(MixBuffer 롤링/청킹 로직), `wav_and_transcript_persistence`(저장 모듈), `headless_synthetic_audio_verification`(셀프테스트) — 프로젝트 고유 자체 구현.

**skill_gap_hypotheses**: brief 상 명시된 갭 없음. 모든 capability가 reuse 또는 직접 구현으로 커버 가능하다고 판단.

---

## References

- Local: `docs/work-items/windows-…/feature-spec.md` | ## Feature Overview
- Local: `docs/work-items/windows-…/feature-plan.md` | ## 목표
- Local: `docs/work-items/windows-…/implementation-design.md` | ## Design Summary
- Local: `docs/task_execution_plan.md` | ## Overview
- Research note: pyaudiowpatch `get_default_wasapi_loopback()` 패턴
- Research note: faster-whisper `transcribe(vad_filter=True, language="ko")` 내장 Silero VAD
- Research note: numpy 사인파 → 16kHz mono WAV → `model.transcribe` 헤드리스 검증 표준
- Workspace note: existing_todo=`.todo.md`, existing_project_board=`project_board_state.json`

---

## Test Strategy

검증은 **헤드리스 가능 우선** 원칙으로 계층화한다. 마이크 없는 CI/헤드리스에서도 핵심 경로가 검증되어야 한다.

### 1. 헤드리스 셀프테스트 (`scripts/selftest.py`, 필수 e2e)

- 합성 사인파(또는 짧은 음성 샘플) → numpy → 16kHz mono WAV 생성.
- `config.detect_device()` 호출 → device 튜플 반환 확인.
- `TranscribeWorker`를 UI 없이 직접 구동, 합성 WAV를 청크 큐에 주입 → `transcribe` 1회 성공·`TranscriptChunk` 반환 검증.
- exit code 0 = 통과. **e2e_command**: `python scripts/selftest.py`.

### 2. 모듈 import / enumerate 테스트

- 모든 `app/*` 모듈 import 무오류(캡처 모듈 지연 로딩으로 비-Windows 통과).
- `enumerate_devices()` 호출 시 예외 없음, 빈 목록 안전 반환 검증(장치 없는 환경 모킹).

### 3. 단위 테스트

- `MixBuffer`: 두 스트림 push 후 청크 경계(VAD/maxlen) 도달 시에만 `pop_chunk` 반환, overlap 유지.
- `config.detect_device()`: CUDA 모킹 실패 시 `("cpu","int8")` 폴백.
- `persistence`: 저장 경로가 `meetings/` 하위로 해석되고 절대경로 리터럴 부재(코딩 컨벤션 테스트와 정합).

### 4. 통합(호출 경로) 테스트

- 녹음 시작→청크 전사→정지→WAV+전사 저장의 함수 호출 체인이 mock 캡처 스트림으로 end-to-end 연결됨을 검증(stub-only 금지, 최소 1개 실제 실행 경로 포함).

### 5. 패키징 검증

- `python build.py`로 onedir 산출 → `dist/` 내 실행 파일 생성 + ctranslate2/onnxruntime DLL 동봉 확인.
- 빌드 산출물에서 셀프테스트 1회 smoke 실행.

> **Episode Hint 준수**: 모든 build/verify 태스크는 실제 `e2e_command`를 가지며, mock-only 테스트는 PASS 처리하지 않는다. approval-gate `status=completed`는 파일 존재 + 금지토큰 0 + e2e exit 0을 모두 충족할 때만 인정한다.