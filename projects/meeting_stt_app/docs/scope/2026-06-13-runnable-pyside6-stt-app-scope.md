# 실행 가능한 PySide6 회의록 STT 데스크톱 앱 — 범위·인터페이스·구현 순서 계약

## Metadata
- **task_id**: frontend_dev_module_1_scope_1
- **stage**: scope (범위와 계약 정의)
- **owner_role**: Frontend Dev
- **status**: fixed (이 문서가 확정되면 build 단계는 이 계약을 변경 없이 따른다)
- **last_updated**: 2026-06-13
- **상위 출처**: `docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md`, `implementation-design.md`
- **문서 언어**: 한국어 (실측 OS 로케일 `ko_KR`; 계약의 `c`는 미해석 POSIX 기본값이므로 프로젝트 전체 문서 세트와 동일하게 한국어로 작성)

---

## 0. 이 문서의 목적

본 문서는 `실행 가능한 PySide6 회의록 STT 데스크톱 앱`이라는 **통합·실행 모듈**의 범위를 고정한다.
feature-spec / implementation-design 에서 이미 **변경 금지로 확정된 아키텍처**를 재논의하지 않는다.
대신 다음 3가지를 못박아 build 단계가 명확화 질문 없이 바로 구현에 들어갈 수 있게 한다.

1. **범위 경계** — 이 모듈이 무엇을 책임지고 무엇을 책임지지 않는가 (sibling 모듈과의 경계).
2. **의존성·산출물** — 모듈 간 `depends_on` 그래프와 모듈별 산출 파일.
3. **구현 순서 고정** — 슬라이스 빌드 순서와 각 슬라이스의 완료 게이트.

> 이 모듈(`app/main.py` 셸 + 통합 배선)은 **재설계가 아니라 구현 진입**이다. 신규 스킬 forge 없이 기존 스택을 **reuse** 한다.

---

## 1. 범위 경계 (Scope)

### 1.1 이 모듈이 책임지는 것 (In Scope)
- **앱 셸**: `app/main.py`, `app/__init__.py` — `QApplication` 부트스트랩, `AppSettings` 로드, `MainWindow` 기동, 종료 처리.
- **통합 배선(integration wiring)**: 캡처→믹싱→청크큐→전사워커→UI→저장 의 end-to-end 연결이 코드상 단선 없이 이어지도록 sibling 모듈을 조립.
- **상태 머신 소유**: `IDLE → INITIALIZING → RECORDING → STOPPING → SAVED`(+`ERROR`) 전환을 메인 스레드 단일 소유로 관리.
- **저장 루트 해석**: 절대경로 하드코딩 없이 `meetings/<session_id>/` 경로를 결정(홈/문서/앱폴더 기반).
- **헤드리스 기동 보장**: 오디오 장치 0개 환경에서도 import·기동이 예외 없이 성공.

### 1.2 sibling 모듈이 책임지는 것 (이 scope 작업의 직접 구현 대상 아님 — 통합만)
| 책임 | 담당 모듈(별도 work-item) |
|------|--------------------------|
| 마이크+loopback 캡처·16kHz mono 리샘플·믹싱·롤링버퍼·원본 WAV 피드 | 오디오 엔진 (M2) |
| faster-whisper 모델 로드(CUDA/CPU 분기)·VAD 청킹·전사 워커 | 전사 워커 (M3) |
| 자막 패널·장치/모델/언어 드롭다운·타이머·레벨 미터 위젯 | UI (M4) |
| WAV·`.txt`/`.md`·세션 메타 JSON 영속화 | 저장/세션 (M5/M6) |
| 합성 오디오 헤드리스 셀프테스트 | QA (M10) |
| requirements.txt / PyInstaller 스펙 / README | 의존성·패키징·문서 (M7/M8/M9) |

> 본 통합 모듈은 위 모듈의 **인터페이스(§3)** 만 소비한다. 내부 구현에 개입하지 않는다.

### 1.3 범위 밖 (Out of Scope — feature-spec 승계)
- 클라우드/온라인 STT API, 화자 분리(diarization), 요약·번역·키워드 추출.
- macOS/Linux 지원(Windows WASAPI 전용).
- 자막 사후 편집기/타임라인 에디터, 모델 파인튜닝.

---

## 2. 의존성과 산출물 (Dependencies & Deliverables)

### 2.1 외부 런타임 의존성 (확정 — 변경 금지)
| 패키지 | 용도 | 비고 |
|--------|------|------|
| `PySide6` | Qt6 GUI, QThread, Signal/Slot | UI 논블로킹 |
| `faster-whisper` | 로컬 STT (CTranslate2 백엔드) | 내장 `vad_filter` 사용 |
| `pyaudiowpatch` | WASAPI loopback + 마이크 캡처 | PyAudio 포크, Windows 전용 |
| `numpy` | 16kHz mono 리샘플·믹싱·RMS | 단일 의존성 |
| `soundfile` (또는 `scipy`) | WAV I/O | 원본 WAV 저장 |
| `PyInstaller` | onedir 패키징 | ctranslate2 DLL·모델 번들 |

> 외부 `webrtcvad` 는 **채택하지 않는다** (faster-whisper 내장 `vad_filter` 로 대체 — 의존성 최소화).

### 2.2 모듈 의존성 그래프 (depends_on)
```
M11(devices/config) ──┐
                      ├─→ M2(audio engine) ──┐
                      │                       ├─→ M5(recorder/writer) ──→ M6(session meta)
M3(stt worker) ───────┼───────────────────────┘
                      │
M2, M3 ───────────────┴─→ M4(UI) ──┐
                                   ├─→ M1(app shell / 통합) ◀── 본 모듈
M5, M6, M11 ───────────────────────┘
M10(selftest) ── 의존: M2, M3, M5 (UI 비의존, 헤드리스)
M7/M8/M9 ── 의존: 전체 (마지막)
```

### 2.3 모듈별 산출 파일 (Deliverables)
| 모듈 | 산출 파일 | 비고 |
|------|-----------|------|
| **M1 앱 셸/통합** *(본 모듈)* | `app/main.py`, `app/__init__.py` | 엔트리포인트 + 배선 |
| M11 장치/설정 | `app/audio/devices.py`, `app/config.py` | enumerate, `AppSettings` |
| M2 오디오 엔진 | `app/audio/capture.py`, `app/audio/mixer.py` | 캡처 스레드, 믹서 |
| M3 전사 워커 | `app/stt/transcriber.py`, `app/stt/worker.py`, `app/stt/types.py` | `TranscriptChunk` SSOT |
| M4 UI | `app/ui/main_window.py`, `app/ui/widgets.py` | 위젯 |
| M5 저장 | `app/io/recorder.py`, `app/io/transcript_writer.py` | WAV, txt/md |
| M6 세션 메타 | `app/io/session.py` | `RecordingSession` SSOT |
| M7 의존성 | `requirements.txt` | 런타임 고정 |
| M8 README | `README.md` | 설치/실행/loopback 주의 |
| M9 패키징 | `build.py`, `meeting_stt.spec` | onedir 스펙 |
| M10 셀프테스트 | `tests/selftest_pipeline.py` | 합성 WAV → 전사 1회 |

> **타입 SSOT**: `RecordingSession`(`app/io/session.py`), `TranscriptChunk`(`app/stt/types.py`), `AppSettings`(`app/config.py`) 는 각각 단일 파일에서만 선언하고 타 모듈은 import 한다. 재선언 금지.

---

## 3. 통합 인터페이스 계약 (Interface Contract)

본 통합 모듈이 소비하는 sibling 경계 인터페이스를 고정한다. build 단계는 시그니처를 변경하지 않는다.

```python
# app/config.py
@dataclass
class AppSettings:
    model_size: str          # "tiny"|"base"|"small"|"medium", 기본 "small"
    language: str            # "ko"|"auto", 기본 "ko"
    mic_device_index: int | None
    loopback_device_index: int | None
    save_root: str | None    # None이면 (홈/문서/앱폴더)/meetings/ 로 해석
    max_chunk_sec: float     # 10~15
    use_vad: bool            # 기본 True
    @classmethod
    def load(cls) -> "AppSettings": ...
    def save(self) -> None: ...

def resolve_save_root(settings: "AppSettings") -> Path: ...   # 절대경로 하드코딩 금지

# app/audio/devices.py
@dataclass
class Device:
    index: int
    name: str
def enumerate_devices() -> tuple[list[Device], list[Device]]: ...   # (mics, loopbacks), 빈 리스트 허용·예외 금지

# app/audio/mixer.py
class AudioMixer:
    level_changed: Signal            # float RMS (UI throttle ~50ms)
    def push_mic(self, frames: np.ndarray) -> None: ...
    def push_loopback(self, frames: np.ndarray) -> None: ...
    def read_chunk(self) -> Optional[np.ndarray]: ...   # VAD 무음 또는 max_chunk_sec 도달 시 16kHz mono 청크 반환

# app/stt/types.py  (SSOT)
@dataclass
class TranscriptChunk:
    chunk_index: int
    start_ts: float
    end_ts: float
    text: str
    language: str
    no_speech_prob: float

# app/stt/transcriber.py
class Transcriber:
    def __init__(self, model_size: str, language: str): ...   # CUDA 감지 시 cuda/float16, 미감지 시 CPU int8
    def transcribe_chunk(self, audio: np.ndarray) -> list[TranscriptChunk]: ...

# app/stt/worker.py
class TranscribeWorker(QThread):
    chunk_ready: Signal              # TranscriptChunk
    def enqueue(self, audio: np.ndarray) -> None: ...
    def stop_and_drain(self) -> None: ...   # 잔여 큐 소진까지 전사 후 종료

# app/io/recorder.py
class WavRecorder:
    def open(self, wav_path: Path) -> None: ...
    def write(self, frames: np.ndarray) -> None: ...
    def close(self) -> None: ...

# app/io/transcript_writer.py
class TranscriptWriter:
    def append(self, chunk: TranscriptChunk) -> None: ...
    def flush(self, txt_path: Path, md_path: Path) -> None: ...

# app/io/session.py  (SSOT)
@dataclass
class RecordingSession:
    session_id: str; started_at: str; ended_at: str
    wav_path: str; transcript_txt_path: str; transcript_md_path: str
    model_size: str; language: str
    mic_device: str; loopback_device: str; duration_sec: float
    def save_json(self, path: Path) -> None: ...
```

### 3.1 통합 모듈(M1)이 보장해야 하는 배선 불변식
- 전사 호출(`Transcriber.transcribe_chunk`)은 **UI 슬롯에서 직접 호출 금지** — 반드시 `TranscribeWorker`(QThread) 경유.
- 상태 전환은 메인 스레드 단독 소유 — 캡처/워커 스레드는 Signal 로만 메인 스레드에 통지.
- 정지 시 순서 고정: 캡처 stop → 스트림 join → 믹서 잔여 flush → 워커 `stop_and_drain` → WAV close → `.txt`/`.md` flush → `RecordingSession` JSON 저장 → 저장 경로 표시.

---

## 4. 구현 순서 고정 (Implementation Order — Locked)

build 단계는 아래 슬라이스 순서를 따른다. 각 슬라이스는 **독립 배포 가능한 작은 단위**이며, 완료 게이트를 통과해야 다음으로 넘어간다. (Karpathy: 작은 슬라이스 + 검증 가능한 완료 기준)

| # | 슬라이스 | 산출 | 완료 게이트(검증) |
|---|----------|------|-------------------|
| S0 | 프로젝트 골격 + 타입 SSOT | `app/` 패키지, `config.py`, `stt/types.py`, `io/session.py`(타입만) | 전 모듈 import 성공(헤드리스), 타입 중복 선언 0 |
| S1 | 장치/설정 레이어 | `devices.py`, `config.py` | `enumerate_devices()` 장치 0개에서 빈 리스트·예외 없음, `resolve_save_root` 절대경로 리터럴 없음 |
| S2 | STT 전사 코어 | `transcriber.py` | 합성 16kHz mono 사인파/샘플 WAV → `transcribe_chunk` 가 `TranscriptChunk`≥1 반환 **(핵심 통과 조건)** |
| S3 | 오디오 엔진 | `capture.py`, `mixer.py` | 합성 프레임 push → `read_chunk` 가 청크 경계에서 16kHz mono 반환 |
| S4 | 전사 워커(스레드/큐) | `worker.py` | `enqueue`→`chunk_ready` Signal, 전사가 워커 스레드에서 수행됨(UI 비블로킹 코드 경로 확인) |
| S5 | 저장/세션 | `recorder.py`, `transcript_writer.py`, `session.py` | WAV + `.txt`/`.md` + `session.json` 이 `meetings/<session_id>/` 에 생성 |
| S6 | UI 레이어 | `main_window.py`, `widgets.py` | 위젯 구성·Signal 연결(헤드리스에서 위젯 생성은 offscreen 가능 범위) |
| S7 | **앱 셸 통합(본 모듈 핵심)** | `main.py` | 시작→자막 append→정지→저장 흐름이 코드상 end-to-end 단선 없이 연결 |
| S8 | 헤드리스 셀프테스트 | `tests/selftest_pipeline.py` | 장치 없이 합성 WAV가 파이프라인 1회 전사 성공 + 배선 e2e 검증 |
| S9 | 의존성·패키징·문서 | `requirements.txt`, `build.py`, `meeting_stt.spec`, `README.md` | spec 에 ctranslate2 `binaries`/모델 `datas`/`hiddenimports` 명시, README 패키징 절차 문서화 |

> **임계 경로**: S2(전사 코어)가 가장 위험 요소 — 먼저 검증한다. S7(통합)이 본 모듈의 실질 완료 지점이며, S8 셀프테스트로 배선 단선을 차단한다.

---

## 5. 완료 기준 (이 scope 작업의 Acceptance)

- [x] 실행 가능한 PySide6 회의록 STT 앱의 범위가 In/Out 경계로 명확히 정리됨 (§1).
- [x] 외부 의존성(§2.1)과 모듈 의존성 그래프(§2.2), 모듈별 산출 파일(§2.3)이 명시됨.
- [x] 통합 인터페이스 계약(§3)과 배선 불변식(§3.1)이 고정됨.
- [x] 구현 순서(S0~S9)와 각 슬라이스 완료 게이트(§4)가 고정됨.

## 6. 다음 단계 (build 진입 핸드오프)
- build 작업자는 **S0 → S9 순서**로 진행하며, S2(전사 코어 1회 전사 성공)와 S7(end-to-end 배선), S8(헤드리스 셀프테스트)을 핵심 게이트로 삼는다.
- 모든 저장 경로는 `meetings/<session_id>/` 상대 경로 기반 — 절대경로 하드코딩 금지(CLAUDE.md 규칙).
- 타입 3종(`RecordingSession`/`TranscriptChunk`/`AppSettings`)은 SSOT 단일 파일 선언.
