# Feature Spec — 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 (M2)

- **work-item**: `audio-engine`
- **task_id**: `frontend_dev_module_2_scope_1`
- **단계(stage)**: scope (범위·인터페이스 고정)
- **소유 역할**: Frontend Dev (오디오 엔진 work-item 소유자)
- **날짜**: 2026-06-13
- **상태**: frozen — build 슬라이스용 계약 고정
- **문서 언어**: 한국어 (`docs/architecture.md` Metadata가 확정한 프로젝트 문서 언어를 승계. OS 로케일 실측 `ko_KR`)
- **바인딩 상위 계약**: `docs/architecture.md` §Current Design(M2), `docs/scope/2026-06-13-runnable-pyside6-stt-app-scope.md`

---

## 0. 전제: 이 work-item은 "이미 구현된 엔진"의 계약 고정이다

baseline grep(`app/audio/*.py`) 결과, 본 work-item의 코어 3개 파일은 **이미 구현·배선 완료** 상태다.

| 파일 | 공개 심볼 | 배선 호출부(단선 아님) |
|------|-----------|------------------------|
| `app/audio/devices.py` | `Device`, `enumerate_devices`, `detect_compute_device` | `app/ui/main_window.py:111` |
| `app/audio/mixer.py` | `AudioMixer`, `to_mono_float32`, `resample_to_16k`, `rms` | `app/main.py:129,136,139,159,210` |
| `app/audio/capture.py` | `CaptureThread`, `FRAMES_PER_BUFFER` | `app/main.py:135,138` |

따라서 본 scope의 산출물은 **새 설계 제안이 아니라 as-built 인터페이스의 동결**이며, 후속 build 슬라이스는
(1) 발견된 믹싱 결함 수정 + (2) 회귀 테스트 보강에 집중한다. 새 추상화·새 라이브러리 도입 금지(과설계 회피).

> **중복 선언/단선 검증 결과(완료 기준 1)**
> - 타입 SSOT: 리샘플/모노화 헬퍼(`resample_to_16k`/`to_mono_float32`)는 `mixer.py`에서 **단 한 번** 선언되고
>   `capture.py`가 import해 소비한다. 중복 선언 없음.
> - `Device` dataclass는 `devices.py`에서만 선언. 중복 없음.
> - 단선 없음: `AudioMixer.push_mic/push_loopback/read_chunk/flush`, `CaptureThread.start/stop`,
>   `enumerate_devices`가 모두 production 호출 경로(`app/main.py`, `app/ui/main_window.py`)에 연결돼 있음.

---

## 1. 기능 범위 (무엇을 한다)

마이크 입력과 시스템오디오(WASAPI loopback)를 **동시에** 캡처하여, 각 스트림을 16kHz mono float32로
정규화하고, 두 스트림을 **시간 정렬 평균 믹싱**한 단일 16kHz mono 스트림을 청크 단위로 내보낸다.
동시에 입력 레벨(RMS)을 UI에 통지한다.

### 범위 안 (in-scope)
- 마이크/loopback **2개 스트림 병렬 캡처** (장치당 1 캡처 스레드).
- 장치 네이티브 샘플레이트·채널 → **16kHz mono float32 `[-1,1]`** 정규화(채널 평균 + 선형 리샘플).
- 두 스트림 **시간 정렬 평균 믹싱** → 단일 16kHz mono 스트림.
- **청크 경계 결정**: VAD 무음 tail 컷 또는 `max_chunk_sec` 도달.
- **RMS 레벨 미터** 시그널 발화(~50ms throttle).
- **graceful degradation**: 한쪽 장치만 있거나(마이크 단독/loopback 단독), `pyaudiowpatch` 미설치,
  장치 0개인 헤드리스 환경에서도 **예외 없이** 동작(캡처는 무동작, enumerate는 빈 목록).

### 범위 밖 (out-of-scope, 다른 work-item)
- faster-whisper 전사(`app/stt/*`, M3).
- WAV/txt/md 영속화(`app/io/*`, M5/M6).
- 펌프 루프·상태 머신·UI 배선(`app/main.py`, `app/ui/*`, M1/M4).
- 풀레이트 원본 WAV 별도 트랙 저장(scope §D2에서 선택 후속으로 보류, 본 엔진은 믹싱 16kHz만 발행).

---

## 2. 데이터 계약 (고정)

| 항목 | 값 | 출처(SSOT) |
|------|-----|-----------|
| 타깃 샘플레이트 | `16000` Hz | `app/config.py:TARGET_SAMPLE_RATE` |
| 채널 | mono (1ch) | 정규화 후 고정 |
| 샘플 포맷 | `numpy.ndarray`, `float32`, 범위 `[-1.0, 1.0]` | 캡처/믹서 공통 |
| 캡처 입력 포맷 | WASAPI `paInt16` PCM, 장치 네이티브 rate/channels | `capture.py` |
| 콜백 프레임 크기 | `FRAMES_PER_BUFFER = 1024` (장치 네이티브 기준) | `capture.py` |
| 청크 길이 상한 | `max_chunk_sec`(기본 12.0초, 10~15 범위) | `AppSettings.max_chunk_sec` |
| 무음 컷 최소 청크 | `MIN_CHUNK_SEC = 1.0`초 | `mixer.py` |
| 무음 판정 RMS | `SILENCE_RMS_THRESHOLD = 0.01` | `mixer.py` |
| 무음 tail 길이 | `SILENCE_TAIL_SEC = 0.4`초 | `mixer.py` |
| 레벨 미터 throttle | `LEVEL_EMIT_INTERVAL_SEC = 0.05`초 | `mixer.py` |

**경계 불변식**: 리샘플·모노화는 **캡처 측**에서 끝낸다. 믹서 `push_*`는 이미 16kHz mono로 정규화된
프레임만 받는다(rate/channels 인자를 받지 않는 고정 시그니처). 이 결정은 architecture.md
"Implementation decisions"와 정합한다.

---

## 3. 공개 인터페이스 (as-built, 동결)

다른 역할(Frontend 배선 `main.py`, UI `main_window.py`)이 소비하는 공개 계약. 시그니처는 변경하지 않는다.

### 3.1 `app/audio/devices.py`
```python
@dataclass
class Device:
    index: int
    name: str

def enumerate_devices() -> tuple[list[Device], list[Device]]
    # (mics, loopbacks). pyaudiowpatch 미설치·장치 0개·WASAPI 미지원 시 예외 없이 ([], []).

def detect_compute_device() -> tuple[str, str]
    # CUDA 감지 시 ("cuda","float16"), 아니면 ("cpu","int8"). (전사기가 소비 — M3 경계)
```

### 3.2 `app/audio/mixer.py`
```python
def to_mono_float32(frames: np.ndarray, channels: int = 1) -> np.ndarray   # int16/int32/float → mono float32 [-1,1]
def resample_to_16k(frames: np.ndarray, src_rate: int) -> np.ndarray       # 선형 리샘플(mono float32 가정)
def rms(frames: np.ndarray) -> float                                        # RMS 레벨(0~1 근처)

class AudioMixer(QObject):           # qt_compat.QObject (PySide6 유무 무관)
    level_changed = Signal(float)
    def __init__(self, max_chunk_sec: float = 12.0, use_vad: bool = True, active_sources: int = 2) -> None
    def push_mic(self, frames: np.ndarray) -> None        # 16kHz mono float32
    def push_loopback(self, frames: np.ndarray) -> None   # 16kHz mono float32
    def read_chunk(self) -> Optional[np.ndarray]          # 청크 경계 도달 시 16kHz mono, 아니면 None
    def flush(self) -> Optional[np.ndarray]               # 정지 시 잔여 전량 반환(없으면 None)
```

### 3.3 `app/audio/capture.py`
```python
FRAMES_PER_BUFFER = 1024

class CaptureThread:
    def __init__(
        self,
        device_index: Optional[int],
        on_frames: Callable[[np.ndarray], None],   # 16kHz mono float32 프레임 콜백
        loopback: bool = False,
    ) -> None
    def start(self) -> None    # device_index=None 또는 pyaudiowpatch 미설치 시 무동작
    def stop(self) -> None     # _stop set + join(timeout=2s)
```

**콜백 계약**: `on_frames`는 캡처 **백그라운드 스레드**에서 발화한다. `main.py`는 이를
`AudioMixer.push_mic`/`push_loopback`에 직접 바인딩한다(Qt 타입은 경계를 넘지 않음 — plain `Callable`).

---

## 4. 데이터 흐름

```
[마이크 장치]  → CaptureThread(mic)  ─ paInt16/native ─→ to_mono_float32 → resample_to_16k ─┐
                                                                                            ├→ AudioMixer
[loopback 장치]→ CaptureThread(loop) ─ paInt16/native ─→ to_mono_float32 → resample_to_16k ─┘   .push_mic / .push_loopback
                                                                                                    │
                                       _drain_into_pending_locked: min(len(mic),len(loop)) 정렬 평균 믹싱
                                                                                                    │
                                                    read_chunk(): VAD tail 무음 또는 max_chunk_sec 컷
                                                                                                    │
                                                    ┌───────────────────────────────────────────────┘
                                          (M1 펌프 스레드가 폴링) → WavRecorder.write + TranscribeWorker.enqueue
                                          level_changed(float) ──→ (M1) → UI LevelMeter
```

정지 순서(M1 `stop()`이 소유, 본 엔진은 stop/flush를 제공): 캡처 `stop()` → 펌프 정지 →
믹서 `flush()` → (M3 worker drain) → ...

---

## 5. 의존성 & 산출물

### 의존(depends_on)
- 외부: `pyaudiowpatch`(WASAPI 캡처·loopback·장치 enumerate), `numpy`(DSP). `requirements.txt`는
  M7(Frontend 패키징) 소유 — 본 엔진은 import만 하고 매니페스트는 소유하지 않는다.
- 내부: `app/config.py`(`TARGET_SAMPLE_RATE`), `app/qt_compat.py`(`QObject`/`Signal` 셰임).
- **소비처(downstream)**: `app/main.py`(M1, 배선·펌프), `app/ui/main_window.py`(M4, enumerate).
- faster-whisper/`ctranslate2`는 `detect_compute_device`가 감지만 하고 직접 import 의존 아님(전사기가 소비).

> **라이브러리 정정**: 상위 task 설명의 "sounddevice/soundcardlib"은 후보 예시였다. **실제 baseline은
> `pyaudiowpatch`**(WASAPI loopback을 단일 백엔드로 지원). 새 라이브러리 도입 없이 as-built를 따른다.

### 산출물 (audio-engine work-item)
1. `app/audio/devices.py` — 장치 enumerate + compute 감지 (구현 완료)
2. `app/audio/mixer.py` — 정규화 헬퍼 + `AudioMixer`(리샘플·믹싱·청킹·레벨) (구현 완료, **결함 1건 — §6**)
3. `app/audio/capture.py` — `CaptureThread` 이중 스트림 캡처 (구현 완료)
4. 회귀 테스트 — 번갈아 push 시 믹싱 정합 단언(신규, build 슬라이스 B2)

---

## 6. 알려진 결함 (build에서 해결할 핵심 항목)

`docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md` §2에서 인계된 **믹싱 타임라인 결함**.

- **증상**: 별도 스레드가 `push_mic`/`push_loopback`을 번갈아 호출하는 정상 패턴에서, 믹서가 두 스트림을
  평균 믹싱하지 않고 **연결(concatenate)** 한다 → 타임라인 2배, 음성 비동기화.
- **근거(실측)**: mic 3.0s + loop 3.0s 입력 시 출력 96000샘플(6.0s, 정상은 48000/3.0s).
- **원인**: `AudioMixer._drain_into_pending_locked()`의 단일 소스 폴백이 "loopback 항구 부재"와
  "loopback이 잠깐 뒤처짐"을 구분하지 못하고, 상대 버퍼가 일시적으로 빈 순간 한쪽을 단독 flush한다.
  생성자 인자 `active_sources`는 저장만 되고 drain 로직에서 **참조되지 않는 dead state**(`mixer.py:88`)이며,
  `main.py:129`는 이 인자를 전달조차 하지 않는다 → 결함의 직접 원인.
- **공개 시그니처 영향 없음**: `push_*`/`read_chunk`/`flush`/`level_changed` 계약은 유지한 채 내부 drain
  로직만 수정 가능.

---

## 7. 인수 기준 (Acceptance — build 검증 게이트)

| # | 기준 | 검증 방법(헤드리스) |
|---|------|---------------------|
| A1 | 헤드리스 import-safe | `import app.audio.{devices,mixer,capture}` 무오류 |
| A2 | enumerate graceful | 장치 0개/미설치 → `enumerate_devices()==([],[])`, 무예외 |
| A3 | 정규화 정합 | `to_mono_float32`/`resample_to_16k` shape·rate·dtype·범위 단언 |
| A4 | **믹싱 정합(결함 회귀)** | mic+loop **번갈아** push → 출력 총 길이 == 입력 길이, 정렬 구간 값 합산(클립) |
| A5 | 청크 경계 | VAD tail 무음 또는 `max_chunk_sec`에서 `read_chunk` 컷, `flush` 잔여 반환 |
| A6 | 단일 소스 graceful | 마이크 단독/loopback 단독에서 정상 단일 스트림 발행 |
| A7 | 캡처 생명주기 | `CaptureThread.start/stop` join 정상(`device_index=None` 무동작) |

A4가 본 work-item의 임계 게이트(§6 결함의 회귀 방지).

---

## 8. 이 task(scope)의 완료 기준 충족

- **범위 명확화**: §1 in/out-of-scope + §3 동결 인터페이스 + §0 as-built 매핑.
- **의존성·산출물 명시**: §5 depends_on(외부 2, 내부 2, 소비처 2) + 산출물 4종.
- **구현 순서 고정**: `implementation-design.md` §3.
- **중복/단선 선확인**: §0 검증 결과(중복 없음, 단선 없음).
