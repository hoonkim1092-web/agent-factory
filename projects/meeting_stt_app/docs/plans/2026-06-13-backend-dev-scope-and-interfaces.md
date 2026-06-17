# Backend Dev — 구현 범위·인터페이스 계약 (고정)

- **task_id**: backend_dev_module_10_scope_1
- **단계(stage)**: scope
- **소유 역할**: Backend Dev (`backend_dev_module_10`)
- **작성**: backend_dev 에이전트
- **날짜**: 2026-06-13
- **상태**: frozen (build 단계용 인터페이스 고정)
- **문서 언어**: 한국어 (`docs/architecture.md`가 확정한 프로젝트 문서 언어를 승계)

이 문서는 **Backend Dev가 무엇을 소유하는지**, 다른 역할이 소비할 **공개 인터페이스(계약)**,
**의존성·산출물**, **구현 순서**를 고정한다. `docs/architecture.md`가 이미 확정한 모듈
레이아웃·데이터 흐름·제약을 **재논의 없이 승계**하고, 그 안에서 backend 경계만 떼어낸다.

---

## 1. 설계 의도 & 역할 경계

단일 프로세스 **PySide6 데스크톱 앱**이라 네트워크 서버는 없다. `backend_dev`의 objective
("서버, 데이터, 외부 연동 레이어를 구현한다")는 **비-UI 엔진·데이터·외부연동 레이어**로 해석한다.

- 외부 연동: `pyaudiowpatch`(WASAPI), `faster-whisper`/`ctranslate2`, CUDA 감지
- 데이터: 공유 타입 + 세션 영속화 (WAV / `.txt` / `.md` / `.json`)
- 엔진: 이중 스트림 캡처, 16kHz mono 리샘플·믹싱, 청크 전사 코어

### 경계 표 (누가 무엇을 소유하는가) — architecture.md 파일명에 정렬

| 모듈/파일 | 소유 | 비고 |
|-----------|------|------|
| `app/config.py` (`AppSettings`) | **Backend** | AppSettings 단일 선언(SSOT) |
| `app/audio/devices.py` | **Backend** | enumerate + `detect_compute_device()` |
| `app/audio/mixer.py` | **Backend** | 16kHz mono 리샘플 + 믹싱 |
| `app/audio/capture.py` | **Backend** | 이중 스트림 캡처(plain thread + 콜백) |
| `app/stt/types.py` (`TranscriptChunk`) | **Backend** | TranscriptChunk 단일 선언(SSOT) |
| `app/stt/transcriber.py` (`WhisperEngine`, `RollingChunker`) | **Backend** | 헤드리스 전사 코어, Qt 비의존 |
| `app/io/session.py` (`RecordingSession`, 저장경로 해석) | **Backend** | RecordingSession 단일 선언(SSOT) |
| `app/io/recorder.py` | **Backend** | WAV writer |
| `app/io/transcript_writer.py` | **Backend** | txt/md writer |
| `app/stt/worker.py` (QThread + `chunk_ready` Signal) | **Frontend** | backend 코어를 감싸는 Qt 어댑터 (§9 D1) |
| `app/ui/*` (패널·드롭다운·레벨미터·타이머) | Frontend | backend 계약 소비 |
| `app/main.py` (셸·상태머신·전체 와이어링) | Frontend | start/stop → 엔진 오케스트레이션 |
| `requirements.txt`, PyInstaller spec, README | Frontend | 패키징/문서 |
| 합성 오디오 헤드리스 셀프테스트 | QA | backend 엔진을 장치 없이 구동 |

### 횡단 아키텍처 규칙 (고정)

> **Backend 엔진 모듈은 PySide6를 import하지 않는다.**
> 엔진은 plain `Callable` 콜백 / thread-safe `queue.Queue`로만 바깥과 통신한다.
> Qt `QThread`/`Signal` 변환은 Frontend의 `app/stt/worker.py` 어댑터가 담당한다.

근거: 완료 기준("장치 없는 헤드리스에서 합성 WAV가 STT 파이프라인을 1회 통과")을 만족하려면
전사 코어가 QApplication 이벤트 루프 없이 동작해야 한다. 또한 Frontend/Backend가 import
사이클 없이 병렬 구현 가능해야 한다. architecture.md의 "전사는 워커 스레드 전용 — UI 블로킹
금지" 제약과 정합한다(워커=Frontend QThread, 전사 코어=Backend 헤드리스).

---

## 2. 데이터 계약 (타입 SSOT)

타입-SSOT 규칙에 따라 아래 3종 dataclass는 **각각 한 파일에서만** 선언하고 나머지는 import한다.
필드는 work-item feature-spec이 고정한 데이터 모델과 동일하다.

```python
# app/stt/types.py
@dataclass(frozen=True)
class TranscriptChunk:
    chunk_index: int
    start_ts: float          # 녹음 시작 기준 초
    end_ts: float
    text: str
    language: str
    no_speech_prob: float = 0.0

# app/config.py
@dataclass
class AppSettings:
    model_size: str = "small"        # tiny|base|small|medium
    language: str = "ko"             # ko|auto
    mic_device_index: Optional[int] = None
    loopback_device_index: Optional[int] = None
    save_root: Optional[str] = None  # None -> session.default_save_root()
    max_chunk_sec: float = 12.0      # 10~15초 윈도우
    use_vad: bool = True

# app/io/session.py
@dataclass
class RecordingSession:
    session_id: str
    started_at: str                  # ISO-8601
    ended_at: Optional[str] = None
    wav_path: Optional[str] = None
    transcript_txt_path: Optional[str] = None
    transcript_md_path: Optional[str] = None
    model_size: str = "small"
    language: str = "ko"
    mic_device: Optional[int] = None
    loopback_device: Optional[int] = None
    duration_sec: float = 0.0
    chunks: list = field(default_factory=list)   # list[TranscriptChunk]
```

**오디오 프레임 포맷(고정):** STT 경로는 mono / 16 kHz / `numpy.ndarray` `float32`,
범위 `[-1.0, 1.0]`. 저장 WAV는 동일 믹싱 스트림을 `int16` PCM @ 16 kHz로 기록한다.

---

## 3. 모듈 인터페이스 (시그니처 고정)

### 3.1 `app/io/session.py` (저장경로 + 세션)
```python
def default_save_root() -> str
    # <문서 폴더 또는 홈>/meetings, 실패 시 <cwd>/meetings. 절대경로 하드코딩 금지.
def session_dir(save_root: str, session_id: str) -> str
def new_session_id(now_iso: str) -> str          # 예: 20260613-142530
```

### 3.2 `app/audio/devices.py`
```python
@dataclass(frozen=True)
class DeviceInfo:
    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_loopback: bool

def enumerate_devices() -> tuple[list[DeviceInfo], list[DeviceInfo]]
    # (mic_inputs, loopback_outputs). 헤드리스/장치부재에서 예외 없이 ([], []) 반환.
def default_loopback_device() -> Optional[DeviceInfo]
def detect_compute_device() -> tuple[str, str]
    # CUDA 감지 시 ("cuda","float16"), 없으면 ("cpu","int8").
```

### 3.3 `app/audio/mixer.py`
```python
def resample_to_16k_mono(samples: "np.ndarray", src_rate: int, channels: int) -> "np.ndarray"
class StreamMixer:
    def __init__(self, target_rate: int = 16000) -> None
    def push_mic(self, frames: "np.ndarray", src_rate: int, channels: int) -> None
    def push_loopback(self, frames: "np.ndarray", src_rate: int, channels: int) -> None
    def pull(self) -> "np.ndarray"      # 정렬된 다음 믹싱 블록(없으면 빈 배열)
```

### 3.4 `app/audio/capture.py`
```python
class DualStreamCapture:
    def __init__(
        self,
        mixer: StreamMixer,
        mic_index: Optional[int],
        loopback_index: Optional[int],
        on_level: Optional[Callable[[float, float], None]] = None,  # (mic_rms, loopback_rms)
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None
    def start(self) -> None     # 마이크/loopback 스레드 기동 → mixer로 push
    def stop(self) -> None      # 스레드 join
    @property
    def mic_only(self) -> bool  # loopback 불가 시 True (graceful degradation)
```

### 3.5 `app/stt/transcriber.py` (헤드리스 코어 — Qt 비의존)
```python
class WhisperEngine:
    def __init__(self, model_size: str = "small", language: str = "ko") -> None
        # devices.detect_compute_device()로 device/compute_type 결정
    def load(self) -> None      # 명시적 모델 로드(UI 진행표시 가능)
    def transcribe(self, audio_16k_mono: "np.ndarray", offset_sec: float) -> list[TranscriptChunk]
        # faster-whisper 내장 vad_filter 사용. offset_sec로 청크 ts를 세션 시간에 매핑.
    @property
    def is_loaded(self) -> bool

class RollingChunker:
    # 롤링 버퍼 누적 + VAD 무음 경계 또는 max_chunk_sec 도달 시 청크 절단.
    def __init__(self, max_chunk_sec: float, use_vad: bool, sample_rate: int = 16000) -> None
    def push(self, audio_16k_mono: "np.ndarray") -> list["np.ndarray"]  # 확정된 청크들 반환
    def drain(self) -> list["np.ndarray"]                               # 정지 시 잔여 flush
```

### 3.6 `app/io/recorder.py` (WAV)
```python
class WavRecorder:
    def __init__(self, wav_path: str, sample_rate: int = 16000) -> None
    def append(self, audio_16k_mono: "np.ndarray") -> None   # float32 -> int16 기록
    def close(self) -> float                                  # 총 길이(초) 반환
```

### 3.7 `app/io/transcript_writer.py` (txt/md)
```python
class TranscriptWriter:
    def __init__(self, txt_path: str, md_path: str) -> None
    def write_chunk(self, chunk: TranscriptChunk) -> None     # 누적
    def finalize(self, session: RecordingSession) -> None     # txt/md flush
```

---

## 4. 계층 통합 계약 (Frontend `app/main.py`가 소비)

Frontend 셸이 배선하는 녹음 생명주기 — backend가 모든 조각을 제공한다.
QThread/Signal 변환은 Frontend `app/stt/worker.py`가 backend 코어를 감싸 담당한다.

```
START:
  mic_in, loopback_out = devices.enumerate_devices()
  engine  = WhisperEngine(settings.model_size, settings.language); engine.load()
  chunker = RollingChunker(settings.max_chunk_sec, settings.use_vad)
  mixer   = StreamMixer()
  cap     = DualStreamCapture(mixer, mic_idx, loop_idx, on_level=<-> Qt signal)
  rec     = WavRecorder(<wav_path>); tw = TranscriptWriter(<txt>, <md>)
  cap.start()
  # Frontend worker(QThread) 루프:
  #   block = mixer.pull(); rec.append(block)
  #   for c in chunker.push(block): chunk = engine.transcribe(c, offset)[...]; emit chunk_ready(chunk)

chunk_ready(chunk):  UI 패널 append  +  tw.write_chunk(chunk)  +  session.chunks.append(chunk)
STOP:
  cap.stop()
  for c in chunker.drain(): emit chunk_ready(engine.transcribe(c, offset))
  dur = rec.close(); tw.finalize(session); session.duration_sec = dur
  RecordingSession JSON 저장(session.py) → wav/txt/md/json 경로를 UI에 표시
```

- `on_level` 등 콜백은 **backend 스레드**에서 발화 → Frontend가 UI 스레드로 marshal.
- 모든 콜백은 plain `Callable`. Qt 타입은 경계를 넘지 않는다.

---

## 5. 의존성 & 산출물

### 의존(depends_on)
- 외부 라이브러리(`requirements.txt`는 Frontend 소유): `faster-whisper`, `pyaudiowpatch`,
  `numpy`, `soundfile`(WAV I/O). backend는 import만 하고 매니페스트는 소유하지 않는다.
- Frontend/QA 모듈에 대한 의존 없음 — backend는 leaf 레벨, 프레임워크 비의존.

### 산출물 (Backend build 단계)
1. `app/config.py` — AppSettings (SSOT)
2. `app/io/session.py` — RecordingSession(SSOT) + 저장경로 해석
3. `app/audio/devices.py` — enumerate + compute 감지
4. `app/audio/mixer.py` — 리샘플 + 믹싱
5. `app/audio/capture.py` — 이중 스트림 캡처
6. `app/stt/types.py` — TranscriptChunk (SSOT)
7. `app/stt/transcriber.py` — WhisperEngine + RollingChunker (헤드리스)
8. `app/io/recorder.py` — WAV writer
9. `app/io/transcript_writer.py` — txt/md writer

모든 모듈은 헤드리스 host에서 import-safe(무거운 import는 lazy/guarded)해야 QA 셀프테스트가
장치·GUI 없이 `transcriber` + `session` + writer 경로를 구동할 수 있다.

---

## 6. 구현 순서 (수직 슬라이스, 고정)

각 단계가 독립 import 가능하고 STT happy-path를 조기에 증명하도록 정렬.

1. **`app/config.py` + `app/io/session.py`** → 검증: import + `default_save_root()`가
   절대경로 하드코딩 아닌 경로 반환, 경로 해석 pytest.
2. **`app/audio/devices.py`** → 검증: 헤드리스에서 `enumerate_devices()`가 예외 없이
   `([],[])`; `detect_compute_device()`가 유효 `(device, compute_type)` 반환.
3. **`app/stt/types.py` + `app/stt/transcriber.py`** → 검증: 합성 16kHz 사인파/샘플 WAV가
   `WhisperEngine.transcribe`로 1회 전사되어 `list[TranscriptChunk]` 반환 **(핵심 완료 기준,
   GUI 없이 충족)**.
4. **`RollingChunker`** (transcriber.py 내) → 검증: `push`가 max_chunk_sec/VAD 경계에서
   청크 절단, `drain`이 잔여 flush.
5. **`app/audio/mixer.py`** → 검증: `resample_to_16k_mono` shape/rate; 두 스트림 믹싱 정렬.
6. **`app/audio/capture.py`** → 검증: loopback 불가 시 `mic_only=True`(graceful);
   스레드 start/stop 정상. (실장치 경로는 수동, 헤드리스는 degradation 분기 커버.)
7. **`app/io/recorder.py` + `app/io/transcript_writer.py`** → 검증: WAV(int16 16k) 기록,
   txt/md flush; `meetings/<session>/` 하위 상대경로.

슬라이스 1→4가 완전 헤드리스 검증 가능한 STT 파이프라인(완료 게이트)을 만든다.
5→7이 라이브 녹음 + 영속화 경로를 완성한다.

---

## 7. 완료 기준 매핑 (meeting_stt_task.md)

| 완료 기준 | 커버 |
|-----------|------|
| import 오류 없이 기동(헤드리스) | 모든 backend 모듈 import-safe (§5) |
| 오디오 장치 enumerate 예외 없음 | `devices.enumerate_devices()` (§3.2, 단계2) |
| 합성 WAV → STT 1회 전사 텍스트 반환 | `transcriber.transcribe()` (§3.5, 단계3) |
| start→청크→stop→WAV+전사 저장 배선 | 통합 계약 (§4) + writer/session.py |
| 저장 경로 절대경로 하드코딩 없음 | `session.default_save_root()` (§3.1) |
| PyInstaller가 ctranslate2 DLL/모델 번들 | Frontend 산출물 (backend 범위 밖) |

---

## 8. 이 task의 완료 기준 충족

- **Backend Dev 구현 범위가 명확히 정리됨**: §1 경계 표 + §5 산출물 9개 파일.
- **의존성과 산출물이 명시됨**: §5 depends_on(외부 4종, 내부 의존 0) + 산출물 목록 + §6 순서.

---

## 9. 가정 & 미결 결정 (조용히 고르지 않고 드러냄)

- **D1 — `app/stt/worker.py` 소유권 (Frontend와 조율 필요).** architecture.md는 worker를
  QThread + `chunk_ready` Signal로 설계했다. Qt 의존이므로 **worker.py는 Frontend 소유**로
  두고, backend는 그 안에 들어갈 헤드리스 코어(`WhisperEngine` + `RollingChunker`)만 제공하는
  것을 권고한다. Frontend가 worker.py를 backend로 넘기길 원하면, §3.5 시그니처를 감싸는 얇은
  QThread 래퍼만 추가하면 되므로 backend 계약 변경은 없다. → Frontend 확인 요청.
- **D2 — 저장 WAV 충실도.** 기준선은 *믹싱 16 kHz mono*를 녹음 WAV로 저장(완료 기준 충족 최소
  경로). feature-spec의 "고품질 원본 WAV 별도 저장"은 풀레이트 별도 트랙으로, **선택 후속**으로
  둔다(과설계 회피). → 풀레이트 보관이 필수인지 owner 확인.
- **D3 — 펌프 루프 소유.** §4는 Frontend worker가 `mixer.pull()`을 드레인. backend 펌프
  헬퍼가 선호되면 `capture.py`에 시그니처 변경 없이 추가 가능. → integration-handoff에서 결정.
- **D4 — 모델 다운로드.** 최초 실행 시 faster-whisper 모델 온라인 다운로드. 오프라인 host는
  사전 번들 필요(패키징=Frontend). backend는 모델 부재 시 `on_error`로 명확히 신호.

---

## 10. Frontend/QA 핸드오프 메모

- **Frontend**: worker.py는 §3.5 헤드리스 코어를 감싸는 QThread 어댑터로 구현. backend
  엔진은 Qt 타입을 노출하지 않으니 콜백/Signal 변환은 UI 스레드에서. AppSettings는
  `app/config.py`(backend) import, 재선언 금지.
- **QA**: 헤드리스 셀프테스트는 `WhisperEngine.transcribe(<합성 16k mono>)` →
  `list[TranscriptChunk]` 비어있지 않음을 단언. 장치 경로는 `enumerate_devices()`가
  `([],[])`를 예외 없이 반환하는지 확인. GUI/QApplication 불필요.
- D1·D2 미결 결정은 build 진입 전 Frontend/owner와 확정 권고.
