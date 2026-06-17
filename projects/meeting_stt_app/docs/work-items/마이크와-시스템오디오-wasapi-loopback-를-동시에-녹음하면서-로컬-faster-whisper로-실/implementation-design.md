# Implementation Design

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | 마이크와-시스템오디오-wasapi-loopback-를-동시에-녹음하면서-로컬-faster-whisper로-실 |
| spec_type | implementation-design |
| source_spec | feature-plan.md (FR-4~FR-7) · feature-spec.md (병렬 생성 중) · role-plan.json |
| status | Draft — 승인 대기 |
| last_updated | 2026-06-13 |

---

## Design Summary

마이크 입력과 시스템 출력 오디오(WASAPI loopback)를 **두 개의 독립 캡처 스레드**로 동시에 받아 16kHz mono로 리샘플·믹싱하고, 롤링 버퍼에서 VAD/최대길이 기준으로 잘라낸 청크를 **별도 워커 스레드**에서 로컬 faster-whisper로 전사한 뒤, Qt 시그널로 UI 자막 패널에 append하는 PySide6 Windows 데스크톱 앱을 구현한다.

핵심 설계 원칙은 **레이어 격리**다:
- **캡처 레이어**(producer)와 **전사 레이어**(consumer)를 thread-safe 큐로 분리해 STT 지연이 오디오 캡처나 UI 렌더링을 절대 막지 않는다.
- **device 자동감지**로 CUDA 가용 시 GPU(float16), 아니면 CPU(int8)로 분기하되, GPU 로드 실패 시 CPU로 자동 fallback한다.
- **장치 비의존 셀프테스트 경로**를 제공해 마이크 없는 헤드리스/CI 환경에서도 합성 WAV를 STT 파이프라인에 직접 주입해 검증한다.

required_capabilities 8개(`dual_source_audio_capture`, `realtime_resample_and_mix`, `vad_chunked_streaming_stt`, `non_blocking_ui_worker_queue`, `session_persistence`, `cuda_cpu_device_autodetect`, `onedir_packaging_with_native_dll`, `headless_synthetic_audio_verification`)는 모두 **기존 라이브러리 역량의 reuse/enhance 범위**로 흡수하며, skill_gap_hypotheses가 비어 있어 신규 forge 대상은 없다. 따라서 본 설계는 외부 라이브러리(pyaudiowpatch, faster-whisper, PySide6)의 조립·배선에 집중하고, 자체 발명은 캡처-믹싱-청킹 동기화 로직에 한정한다.

**기술 선택 근거**: faster-whisper(ctranslate2 backend)는 오프라인·무료·int8 양자화로 CPU에서도 실용적 처리량을 내며 내장 `vad_filter`로 청크 무음 처리를 위임할 수 있어 추가 VAD 의존성을 제거한다. pyaudiowpatch는 PyAudio fork로 WASAPI loopback을 표준 PortAudio 인터페이스로 노출해 마이크와 시스템오디오를 동일 API로 다룰 수 있다. PySide6는 LGPL Qt6 공식 바인딩으로 시그널/슬롯 기반 스레드 안전 UI 갱신을 제공한다.

---

## Planned Modules

| 모듈 | 패키지 경로(제안) | 책임 | owner |
|------|------------------|------|-------|
| frontend_dev_module_1 | `app/main.py` | 앱 진입점·셸·컴포넌트 와이어링·생명주기 | Frontend Dev |
| frontend_dev_module_2 | `app/audio/capture.py`, `app/audio/mixer.py` | 마이크·loopback 동시 캡처 스레드, 리샘플·믹싱, 롤링 버퍼 | Frontend Dev |
| frontend_dev_module_3 | `app/stt/worker.py`, `app/stt/engine.py` | faster-whisper 로더, 청크 전사 워커 스레드/큐 | Frontend Dev |
| frontend_dev_module_4 | `app/ui/main_window.py`, `app/ui/widgets.py` | 자막 패널·장치 드롭다운·모델/언어 선택·타이머·레벨 미터 | Frontend Dev |
| frontend_dev_module_5 | `app/persistence/session_store.py` | WAV·전사 .txt/.md·세션 JSON 영속화 | Frontend Dev |
| qa_engineer_module_6 | `tests/selftest_synthetic.py` | 합성 사인파/샘플 WAV로 STT 파이프라인 1회 통과 검증 | QA Engineer |
| frontend_dev_module_7 | `requirements.txt` | 의존성 명세(고정 버전 권장) | Frontend Dev |
| frontend_dev_module_8 | `packaging/meeting_stt.spec`, `build.py` | PyInstaller onedir 스펙·빌드 스크립트 | Frontend Dev |
| frontend_dev_module_9 | `README.md` | 설치·실행·시스템오디오 캡처 주의사항 | Frontend Dev |
| backend_dev_module_10 | `app/audio/devices.py`, `app/stt/device_detect.py` | 장치 enumerate, WASAPI loopback 후보 탐색, CUDA/CPU 자동감지 | Backend Dev |

**모듈 경계 계약**: 모듈2(캡처)는 `queue.Queue[np.ndarray]`로 청크를 모듈3(전사)에 넘기고, 모듈3은 `Signal(TranscriptChunk)`로 모듈4(UI)에 결과를 푸시한다. 모듈10(devices)은 모듈2·3에 `AudioDeviceConfig`/device 문자열을 공급하는 순수 조회 레이어다. 이 세 경계가 스레드 간 단방향 데이터 흐름을 강제한다.

---

## Data Flow

```
[마이크 장치] ──capture thread A──┐
                                  ├──► [Mixer] ──16kHz mono──► [Rolling Buffer]
[시스템 출력 loopback] ─thread B──┘                                   │
                                                          VAD무음 or 10~15초 도달
                                                                     │
                                                          chunk(np.ndarray)
                                                                     ▼
                                                        [transcription Queue]  ◄── backpressure
                                                                     │
                                                          STT worker thread (1개)
                                                                     │
                                                  faster-whisper.transcribe(vad_filter)
                                                                     │
                                                          TranscriptChunk
                                                                     │
                                                       Qt Signal(emit, 스레드 안전)
                                                                     ▼
                                                  [UI 자막 패널 append] (메인 스레드)

[원본 고품질 PCM] ──별도 누적──► [WAV writer] ──정지 시──► meetings/<session>/audio.wav
[TranscriptChunk 누적] ──정지 시──► transcript.txt / transcript.md
[RecordingSession 메타] ──정지 시──► session.json
```

**두 갈래 분기 설명**: 캡처 스레드는 (1) 실시간 전사용 16kHz mono 믹스 스트림과 (2) 영속화용 고품질 원본 PCM을 **동시에** 갈래로 흘린다. 전사 경로는 손실 압축·다운샘플이 허용되지만 저장 경로는 원본 품질을 유지한다. 이는 "실시간 자막"과 "고품질 녹음"이라는 두 목표가 서로 다른 품질 요구를 갖기 때문이다.

**backpressure 처리**: CPU int8에서 전사가 청크 생성보다 느릴 경우(R3), 큐에 maxsize를 두고 가득 차면 가장 오래된 청크를 드롭하거나 청크 길이를 늘려 누적 지연을 방지한다. 드롭 시 UI에 `[일부 구간 처리 지연]` 표시로 사용자에게 알린다.

---

## Event Sequence / Phase Flow

전체 실행은 5개 Phase의 상태 머신으로 동작한다. RecordingSession은 `IDLE → RECORDING → STOPPING → SAVED`의 상태를 거치며, 셀프테스트는 별도 `SELFTEST` 경로로 분기한다.

### Phase 1 — INIT (앱 기동·장치 enumerate)
- **진입 조건**: 앱 프로세스 시작(`app/main.py` 실행).
- **핵심 이벤트**:
  - 모든 모듈 import (헤드리스 검증 1번 항목 — import 오류 0).
  - 모듈10이 `devices.enumerate()`로 마이크·시스템출력 장치 목록 조회 → UI 드롭다운 채움.
  - `device_detect.probe()`로 CUDA 가용성 판정, 모델 크기 기본값 `small` 설정.
  - 장치가 0개여도 예외 없이 빈 목록 반환(R6 — UI는 "장치 없음" 비활성 상태로 진입).
- **다음 Phase 전환 트리거**: 사용자가 모델·언어·장치 선택 후 **[녹음 시작]** 클릭.

### Phase 2 — RECORDING (캡처·청킹·실시간 전사)
- **진입 조건**: 녹음 시작 클릭 + RecordingSession 상태 `IDLE → RECORDING`.
- **핵심 이벤트**:
  - 캡처 스레드 A(마이크)·B(loopback) 기동, faster-whisper 모델 lazy 로드(GPU 실패 시 CPU fallback, R5).
  - Mixer가 양쪽 스트림을 16kHz mono로 리샘플·믹싱(mix_gain 적용, R2).
  - 롤링 버퍼가 누적 → `vad_filter` 무음 감지 또는 10~15초 최대 길이 도달 시 청크를 전사 큐에 enqueue.
  - STT 워커가 청크를 dequeue → `transcribe(language="ko" or "auto", vad_filter=True)` → TranscriptChunk emit.
  - UI 메인 스레드가 시그널 수신 → 자막 패널 append, 타이머·레벨 미터 갱신(UI 무블로킹 — 모든 STT는 워커 스레드).
  - 원본 PCM은 별도 갈래로 WAV writer에 계속 누적.
- **다음 Phase 전환 트리거**: 사용자가 **[정지]** 클릭.

### Phase 3 — STOPPING (캡처 종료·큐 드레인)
- **진입 조건**: 정지 클릭 + 상태 `RECORDING → STOPPING`.
- **핵심 이벤트**:
  - 캡처 스레드 A·B에 stop 신호 → 버퍼 잔여분을 마지막 청크로 flush.
  - 전사 큐를 완전히 드레인(잔여 청크 전사 완료까지 대기, UI는 "마무리 중" 표시).
  - WAV writer 파일 핸들 close, 원본 스트림 finalize.
- **다음 Phase 전환 트리거**: 큐 드레인 완료 + 모든 워커 join.

### Phase 4 — SAVING (영속화)
- **진입 조건**: 큐 드레인 완료.
- **핵심 이벤트**:
  - 모듈5가 저장 경로 결정 — 절대경로 하드코딩 없이 `Path.home()/Documents` 또는 앱 실행 폴더 하위 `meetings/<session_id>/` 생성(경로 위생 — 검증 5번 항목).
  - `audio.wav`(원본), `transcript.txt`·`transcript.md`(누적 청크), `session.json`(RecordingSession 메타) 저장.
  - UI 저장 경로 표시, 상태 `STOPPING → SAVED → IDLE`.
- **다음 Phase 전환 트리거**: 저장 완료 → IDLE 복귀(재녹음 가능).

### Phase 5 — SELFTEST (헤드리스 장치 비의존 검증)
- **진입 조건**: CI/헤드리스에서 `selftest_synthetic.py` 직접 실행(Phase 1~4와 독립 경로).
- **핵심 이벤트**:
  - 장치 enumerate를 **우회**하고 합성 사인파/샘플 WAV를 생성(R6 회피).
  - 합성 WAV를 STT 엔진에 직접 주입 → `transcribe()` 1회 호출 → 전사 텍스트 반환 확인.
  - import·STT 파이프라인 통과·저장 흐름을 assertion으로 검증, exit code 0/1 반환.
- **다음 Phase 전환 트리거**: 검증 통과/실패 → 프로세스 종료(CI gate).

---

## Interface Impact

이 work item은 **그린필드** 신규 앱이므로 기존 공개 API 변경은 없다. 새로 정의되는 모듈 간 인터페이스:

| 인터페이스 | 시그니처(제안) | 호출 방향 |
|-----------|---------------|----------|
| `devices.enumerate() -> list[DeviceInfo]` | 장치 목록 반환, 빈 목록 허용 | 모듈10 → 모듈4 |
| `device_detect.probe() -> DeviceProfile` | `{device, compute_type, available}` | 모듈10 → 모듈3 |
| `AudioCapture.start(cfg: AudioDeviceConfig)` | 캡처 스레드 기동 | 모듈1 → 모듈2 |
| `Mixer.read_chunk() -> np.ndarray \| None` | 청크 준비 시 반환 | 모듈2 내부 |
| `STTWorker.submit(chunk: np.ndarray)` | 큐 enqueue, 논블로킹 | 모듈2 → 모듈3 |
| `STTWorker.chunk_ready: Signal(TranscriptChunk)` | Qt 시그널 | 모듈3 → 모듈4 |
| `SessionStore.save(session, chunks, wav_pcm)` | 영속화 진입점 | 모듈1 → 모듈5 |
| `run_selftest(wav_path \| None) -> bool` | 합성 WAV 1회 전사 | 모듈6 → 모듈3 |

**계약 안정성**: TranscriptChunk·RecordingSession·AudioDeviceConfig 3개 엔티티는 feature-plan에서 **계약으로 동결**되었으므로 필드 추가는 가능하되 기존 필드 의미 변경은 금지한다. 셀프테스트(모듈6)는 모듈3의 STT 엔진 인터페이스에만 의존하고 UI·캡처 레이어에 의존하지 않아 장치 비의존성을 보장한다.

---

## State And Data Model

### 상태 머신 (RecordingSession lifecycle)

```
IDLE ──[녹음 시작]──► RECORDING ──[정지]──► STOPPING ──[큐 드레인]──► SAVING ──[저장 완료]──► IDLE
                          │
                          └──[GPU 로드 실패]──► (CPU fallback, RECORDING 유지)
```

### 데이터 모델 (계약 고정)

**RecordingSession** (storage: json)
```
session_id        : str   (예: 20260613_155930)
started_at        : str   (ISO8601)
ended_at          : str   (ISO8601)
wav_path          : str   (meetings/<session>/audio.wav, 상대 경로)
transcript_path   : str   (meetings/<session>/transcript.txt|md)
model_size        : str   (tiny|base|small|medium, 기본 small)
language          : str   (ko|auto)
mic_device        : str
loopback_device   : str
```

**TranscriptChunk** (storage: json — session.json 내 배열 또는 별도 chunks.jsonl)
```
chunk_index   : int
start_time    : float   (세션 기준 초)
end_time      : float
text          : str
language      : str
avg_logprob   : float    (faster-whisper segment 신뢰도)
```

**AudioDeviceConfig** (storage: memory — 영속화 안 함)
```
mic_index      : int
loopback_index : int
sample_rate    : int     (캡처 원본, 믹스는 16000 고정)
channels       : int
mix_gain       : float   (마이크/시스템 믹싱 비율, 기본 1.0)
```

**설계 근거**: AudioDeviceConfig는 런타임 전용(memory)이라 세션마다 재선택되며 저장하지 않는다 — 장치 인덱스는 재부팅·장치 변경 시 무효화되므로 영속화하면 stale 참조 위험이 있다. 대신 RecordingSession에는 장치 **이름**(mic_device/loopback_device)만 기록해 재현 정보를 남긴다.

---

## Compatibility Considerations

- **OS**: Windows 11 전용. WASAPI loopback은 Windows API이므로 macOS/Linux는 Non-Goal. `app/audio/capture.py`는 import 시점에 플랫폼 분기 없이 pyaudiowpatch를 직접 의존하나, 셀프테스트(모듈6)는 합성 WAV 경로라 비-Windows CI에서도 STT 부분만은 동작 가능(단, pyaudiowpatch import가 비-Windows에서 실패하면 캡처 모듈을 lazy import로 격리해 셀프테스트를 보호).
- **Python**: 3.11 고정. faster-whisper/ctranslate2 wheel 호환성 기준.
- **CUDA/cuDNN**: GPU 경로는 선택적. 버전 불일치 시(R5) CPU int8로 자동 fallback하므로 GPU 부재 환경과 호환.
- **기존 워크스페이스 산출물**: `.todo.md`, `project_board_state.json`, 기존 work-items 3건과 동일 디렉터리에서 충돌 없이 확장. 신규 코드는 `app/` 하위 패키지로 격리.
- **모델 가중치**: faster-whisper 모델은 최초 실행 시 HuggingFace에서 다운로드되거나 onedir 빌드에 동봉. 오프라인 배포본은 동봉 경로 우선.

---

## Migration Requirement

신규 그린필드 앱이므로 **데이터 마이그레이션·스키마 변환·하위 버전 호환 작업은 없다.** 기존 시스템에서 이관할 상태가 존재하지 않으며, RecordingSession/TranscriptChunk JSON 포맷이 v1 초기 스키마다.

향후 스키마 진화 대비:
- session.json에 `schema_version` 필드를 추가해 두는 것을 권장(미래 호환). 다만 본 슬라이스에서는 계약 동결 필드 외 추가를 최소화하므로 선택 사항.
- 모델 가중치 캐시 디렉터리는 사용자 홈 하위 표준 경로(`~/.cache/huggingface` 또는 앱 지정)를 사용해 재설치 시 재다운로드를 피한다.

---

## Risks

feature-plan Risks(R1~R6)를 설계 레벨 완화책과 함께 재확인한다. required_capabilities 조달은 전부 기존 라이브러리 reuse이므로 **스킬 갭 리스크는 없고**, 리스크는 라이브러리 통합·런타임 동기화에 집중된다.

| ID | 리스크 | 설계 완화책 | 잔여 위험 |
|----|--------|------------|----------|
| R1 | WASAPI loopback이 기본 스피커를 못 잡음 | 모듈10이 loopback 후보를 명시 enumerate, UI 드롭다운에서 사용자 선택. 실패 시 마이크 단독 fallback | 일부 가상 오디오 드라이버는 후보에 안 보일 수 있음 |
| R2 | 두 소스 샘플레이트·버퍼 드리프트 | 양쪽 16kHz mono 통일, 버퍼 큐 길이 보정, mix_gain 게인 정규화 | 장시간 녹음 시 누적 드리프트 — 주기적 리싱크 필요 |
| R3 | CPU int8가 청크보다 느려 자막 누적 지연 | 큐 maxsize backpressure, tiny/base 모델 선택 제공, 청크 길이 가변 | 저사양 CPU에서 medium은 실시간 불가 |
| R4 | PyInstaller가 ctranslate2 DLL·모델 누락 | spec `binaries`/`datas`에 명시 포함, 빌드 후 dist 스모크 검증 절차 문서화 | ctranslate2 버전업 시 DLL 경로 변동 |
| R5 | CUDA/cuDNN 불일치로 GPU 로드 실패 | device probe + try/except CPU fallback 검증 | fallback 시 처리량 저하(R3로 연결) |
| R6 | 헤드리스에서 장치 enumerate 빈 목록 | 셀프테스트가 합성 WAV 직접 주입, enumerate 우회 경로 | 캡처 모듈 자체의 통합 검증은 실장치 필요 |

---

## Alternatives Considered

1. **VAD 라이브러리 분리 (webrtcvad/silero) vs faster-whisper 내장 vad_filter** — 내장 `vad_filter` 채택. 별도 VAD는 의존성·튜닝 부담이 크고, 청킹 트리거는 "최대 길이 10~15초"가 1차 기준이며 무음 감지는 보조이므로 내장으로 충분. 단어 단위 partial token은 Non-Goal이라 정밀 VAD 불필요.

2. **단일 캡처 스트림(믹서 장치) vs 두 스레드 분리 캡처** — 두 스레드 분리 채택. Windows에서 마이크+시스템을 미리 믹스한 가상 장치(Stereo Mix)는 드라이버 의존적이고 비활성인 경우가 많아 신뢰성이 낮다. pyaudiowpatch로 각각 잡아 앱 레벨에서 믹싱하면 mix_gain 제어와 장치 선택 자유도를 확보한다.

3. **전사를 asyncio vs threading** — threading(워커 스레드) 채택. faster-whisper의 `transcribe()`는 동기 CPU/GPU 바운드 작업이라 asyncio 이벤트 루프에서 실행하면 루프를 블로킹한다. PySide6와의 통합도 QThread/시그널이 표준이라 threading + queue가 자연스럽다.

4. **onedir vs onefile 패키징** — onedir 채택(확정 제약). onefile은 실행 시 임시 폴더에 ctranslate2 DLL·모델을 매번 압축 해제해 기동이 느리고 대용량 모델 동봉에 불리하다. onedir은 DLL/모델을 폴더에 펼쳐 두어 기동이 빠르고 디버깅이 쉽다.

5. **전사 결과 저장 포맷 .txt만 vs .txt+.md** — 둘 다 생성(FR-7 충족). .txt는 단순 연속 텍스트, .md는 타임스탬프·청크 구분이 있는 구조화 버전으로 회의록 활용도를 높인다.

---

## Design Evidence

### 근거 (source-backed claims)
- **FR-5 STT 엔진**: CUDA 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`, 기본 모델 `small` — `feature-spec.md`. → Phase 1 device probe + Phase 2 모델 로드에 반영.
- **FR-7 영속화**: 정지 시 `meetings/<session>/...wav`와 전사 `.txt`/`.md` 자동 저장 — `feature-spec.md`. → Phase 4 SAVING + 모듈5.
- **FR-6 UI**: 시작/정지·장치 드롭다운·모델·언어 선택·자막 패널·타이머·레벨 미터·저장 경로 표시 — `feature-spec.md`. → 모듈4 + Phase 1/2.
- **FR-4 VAD 청크 스트리밍**: 롤링 버퍼 + `vad_filter` 또는 10~15초 최대 길이, 기본 `ko`/`auto` — `feature-spec.md`. → 모듈2/3 + Phase 2.

### 검증 기준 (verification_focus)
구현 검증 시 다음을 명시적으로 통과시킨다:
1. **모듈 import 무오류** — Phase 1 헤드리스 기동, `python -c "import app.main"` 성공.
2. **장치 enumerate 예외 없음** — 모듈10이 빈 목록 포함 모든 경우 예외 없이 반환(R6).
3. **합성 WAV STT 1회 통과** — 모듈6 셀프테스트가 합성 사인파/샘플 WAV로 전사 텍스트 반환(Phase 5).
4. **end-to-end 코드 연결** — 녹음 시작→청크 전사→정지→WAV+전사 저장이 Phase 1~4로 코드상 연결.
5. **경로 위생** — `meetings/` 상대 경로, 절대경로 하드코딩 0(CLAUDE.md 규칙 + 테스트).
6. **PyInstaller 스펙 native 포함** — spec `binaries`/`datas`에 ctranslate2 DLL·모델 명시(모듈8).

### 스킬 조달 신호 (reuse/enhance/forge)
- **skill_gap_hypotheses 비어 있음** — 신규 forge 대상 없음.
- required_skills 8종(pyside6_gui_development, wasapi_loopback_audio_capture, realtime_audio_buffering_and_resampling, faster_whisper_streaming_transcription, thread_safe_worker_queue, wav_and_transcript_persistence, pyinstaller_onedir_packaging, headless_synthetic_audio_selftest)은 전부 **reuse/enhance** — 기존 라이브러리 역량의 조립으로 흡수하며 별도 forge 절차 없이 모듈 구현에 통합.
- 따라서 본 설계의 위험·복잡도는 "신규 역량 개발"이 아니라 "검증된 라이브러리의 정확한 배선과 스레드 동기화"에 집중된다.

---

## References

- `docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md` — FR-4(VAD 청크 스트리밍), FR-5(STT 엔진), FR-6(UI 레이어), FR-7(영속화), Feature Overview, Outputs
- `feature-plan.md` (본 work item) — Scope·데이터 모델·Risks·Success Metrics
- `role-plan.json` — 3역할·10모듈·30태스크 분해
- `project_board_state.json` · `.todo.md` — 기존 프로젝트 보드/todo
- Tech stack: Python 3.11 · PySide6(Qt6) · faster-whisper(ctranslate2) · pyaudiowpatch(WASAPI loopback) · numpy · soundfile · scipy(resample) · PyInstaller(onedir)

---

## Test Strategy

검증은 **장치 비의존 자동 검증**과 **실장치 수동 검증** 두 층으로 나뉜다. CI는 전자만 게이트로 사용한다.

### 1. 헤드리스 자동 검증 (CI gate — 모듈6)
- **import 스모크**: `app/` 전 모듈 import 오류 0 검증. pyaudiowpatch import는 lazy 격리해 비-Windows에서도 STT 경로 통과.
- **합성 오디오 STT 셀프테스트**: 440Hz 사인파 또는 샘플 WAV를 생성 → `STTWorker`/`engine.transcribe()`에 직접 주입 → 전사 텍스트(빈 문자열 아님 또는 segment 1개 이상) 반환 확인. exit code 0/1.
- **장치 enumerate 안전성**: 모듈10 `enumerate()`가 장치 0개 환경에서 예외 없이 빈 목록 반환.
- **경로 위생 테스트**: 저장 경로 생성 로직에 절대경로 리터럴(`C:\`, `/Users/`, `/home/`) 부재 검증(정적 grep 또는 단위 테스트).

### 2. 영속화 단위 테스트 (모듈5)
- 가짜 TranscriptChunk 배열 + 더미 PCM으로 `SessionStore.save()` 호출 → `meetings/<session>/`에 audio.wav·transcript.txt·transcript.md·session.json 4개 생성 확인.
- RecordingSession/TranscriptChunk JSON 직렬화 round-trip(저장→로드→필드 일치) 검증.

### 3. 스레드 동기화 검증 (모듈2/3)
- Mixer가 양쪽 합성 스트림을 16kHz mono로 정규화하는지(샘플레이트·채널 단언).
- 전사 큐 backpressure: maxsize 초과 시 드롭 동작 검증(R3 — UI 블로킹 없음을 큐 논블로킹 enqueue로 보장).

### 4. end-to-end 흐름 검증 (코드 연결 — Success Metric 2)
- 합성 캡처 스트림으로 Phase 2→3→4를 헤드리스 구동(UI 없이 핵심 파이프라인만) → 녹음 시작→청크 전사→정지→파일 저장이 실제 호출 체인으로 이어지는지 통합 테스트.

### 5. 패키징 스모크 (모듈8 — 수동/선택 CI)
- `build.py` 실행 → `dist/` onedir 생성 확인.
- spec에 ctranslate2 DLL·모델이 `binaries`/`datas`로 포함됐는지 정적 검사 + dist 기동 1회 스모크(R4).

### 6. 실장치 수동 검증 (Windows, 비-CI)
- 실제 마이크+시스템오디오 동시 캡처, loopback 후보 선택, 실시간 자막 append, GPU/CPU 경로, CUDA fallback(R5)을 수동 체크리스트로 확인.

**검증 우선순위**: Success Metrics 5개(헤드리스 기동·end-to-end 연결·패키징 문서화·장치 비의존 셀프테스트·경로 위생)를 done 정의로 사용하며, 1~4번 자동 검증이 모두 통과해야 work item을 완료로 간주한다.